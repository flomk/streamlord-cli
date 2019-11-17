import argparse
import ctypes
import json
import math
import re
import shlex
import subprocess
import sys

import requests
from bs4 import BeautifulSoup


class StreamLord(object):
    def __init__(self, *args, **kwargs):
        self.s = requests.Session()
        self.s.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:69.0) Gecko/20100101 Firefox/69.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
        self.generic_regex = re.compile(
            r'[\"|\'](.*?)[\"|\']\..*?(.*?)\(([^\(]+)\)')
        self.from_char_regex = re.compile(r'String\.fromCharCode\(([^\)]+)\)')
        self.add_cookie_session()

    def _soupify(self, html, parser='html.parser'):
        return BeautifulSoup(html, parser)

    def add_cookie_session(self):
        webpage = self.s.get('http://www.streamlord.com').text
        cookie = self.parse_cloudflare_cookie(webpage).split('=')
        self.s.cookies.update({
            cookie[0]: cookie[1],
        })

    def space_make(self, int_in):
        int_float = int_in/2
        if int_in % 2 != 0:
            return [math.floor(int_float), math.ceil(int_float)]
        else:
            return [int(int_float), int(int_float)]

    def parse_generic(self, m):
        str_part = m.group(1)
        prototype_method = m.group(2).lstrip()
        numbers = m.group(3)
        if ',' in numbers:
            nums = numbers.split(',')
            srt, stp = int(nums[0]), int(nums[1])
        if prototype_method == "charAt":
            return str_part[int(numbers)]
        elif prototype_method == "substr":
            return self.substr(str_part, srt, stp)
        elif prototype_method == "slice":
            return str_part[slice(srt, stp)]

    def baseN(self, num, b, numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
        return ((num == 0) and numerals[0]) or (self.baseN(num // b, b, numerals).lstrip(numerals[0]) + numerals[num % b])

    def decrypt_js(self, p, a, c, k, e=None, d=None):
        def e(c):
            return self.baseN(c, 36)
        while (c):
            c -= 1
            if (k[c]):
                p = re.sub("\\b" + e(c) + "\\b",  k[c], p)
        return p

    def rshift(self, val, n):
        return ctypes.c_int(val >> n).value if val >= 0 else ctypes.c_int((val+0x100000000) >> n).value

    def substr(self, str_in, start, stop):
        if start > stop:
            return str_in[start:stop+len(str_in)]
        else:
            return str_in[start:stop]

    def parse_part(self, p):
        generic_match = re.search(self.generic_regex, p)
        from_char_match = re.search(self.from_char_regex, p)
        if generic_match is not None:
            return self.parse_generic(generic_match)
        elif from_char_match is not None:
            try:
                return chr(int(from_char_match.group(1)))
            except ValueError:
                return chr(int(from_char_match.group(1), 16))
        else:
            return p[1:-1]

    def parse_cloudflare_cookie(self, html, verbose=False):
        s = {}
        l = 0
        U = 0
        c = 0
        u = 0
        i = 0
        obfuscated_part = re.search(r'S=\'(.*?)\';L', html).group(1)
        if verbose:
            print(obfuscated_part)
        S = obfuscated_part
        A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
        L = len(S)
        r = ''
        for u in range(0, 64):
            s[A[u]] = u

        for i in range(0, L):
            if S[i] != "=":
                si = S[i]
            c = s[si]
            U = ctypes.c_int(U << 6).value + c
            l += 6
            while l >= 8:
                l -= 8
                u_part = self.rshift(U, l)
                a = u_part & 0xff
                if a or (i < (L - 2)):
                    r += chr(a)
        splits = (r.split(';document'))
        codes = splits[0]

        cookie = re.split(r'^.*?=', codes)[1]
        cookies = list(map(lambda x: x.strip(), cookie.split('+')))
        cookies = list(filter(lambda x: len(x) > 2 and (x != "''"), cookies))
        more = [self.parse_part(c) for c in (cookies)]
        cookie_name_parts = [c.strip() for c in re.split(
            r'^.*?=', splits[1])[1].split('+')[:-2]]
        cookie_name = ''.join([self.parse_part(cookie_part)
                               for cookie_part in cookie_name_parts])
        cookie_value = ''.join(more)
        final_cookie = f"{cookie_name}{cookie_value}"
        return final_cookie

    def get_streamlord_url(self, streamlord_url, cookie=None, soupify=False):
        response = self.s.get(streamlord_url).text
        if soupify:
            return self._soupify(response)
        else:
            return response

    def get_stream_url(self, src_page):
        m = re.search(
            r'}\(\'(.*?)\',([\d]+),([\d]+),\'(.*?)\'.*?,([\d]+),([^$]+)', src_page).groups()
        p, a, c, k, e, d = m
        decrypted_sources = self.decrypt_js(
            p, int(a), int(c), k.split('|'), int(0), {})
        if decrypted_sources.startswith("\"") and decrypted_sources.endswith("\""):
            return decrypted_sources[1:-1]
        return decrypted_sources

    def get_media_info(self, in_soup):
        section = in_soup.find(
            'article', attrs={'id': 'movie-description-wrapper'})
        poster = section.select('div.floating-movie img')[0].attrs.get('src')
        title = section.find(
            'div', attrs={'class': 'movie-title'}).text.strip()
        imdb_rating = section.find(
            'p', attrs={'class': 'search-rating'}).text.strip()
        summary = section.find(
            'p', attrs={'class': 'movie-summary'}
        ).text.strip()
        starring = [star.strip() for star in section.find(
            'p', attrs={'class': 'movie-starring'}
        ).text.strip().split('/')]

        meta_info = in_soup.select('#description-ul > #description-ul td')[:-1]
        meta_info = [m.select('li')[1].text.strip() for m in meta_info]
        return {
            'poster': poster,
            'title': title,
            'rating': imdb_rating,
            'summary': summary,
            'starring': starring,
            'meta': meta_info
        }

    def parse_episode_li(self, in_soup):
        title = in_soup.find('a', attrs={'class': 'head'}).find(
            text=True, recursive=False)
        episode = re.search(r'([\d]+)', in_soup.find('span').text).group(1)
        url = in_soup.find('a', attrs={'class': None}).attrs.get('href')
        return {
            'title': title,
            'episode': episode,
            'url': 'http://www.streamlord.com/{}'.format(url)
        }

    def parse_season_sect(self, in_soup):
        season = in_soup.find('div', attrs={'class': 'col'}).text
        season = re.search(r'([\d]+)', season).group(1)
        episodes = [self.parse_episode_li(li) for li in in_soup.find_all('li')]
        return {
            'season': season,
            'episodes': episodes
        }

    def parse_episodes(self, in_soup):
        section = in_soup.find(
            'div', attrs={'id': 'season-wrapper'})
        sections = section.find_all('ul', attrs={'id': 'improved'})
        return [self.parse_season_sect(sect) for sect in sections]

    def parse_show(self, in_soup):
        media_info = self.get_media_info(in_soup)
        show_info = self.parse_episodes(in_soup)
        return {
            'info': media_info,
            'show': show_info
        }

    def get_show(self, url):
        webpage = self.get_streamlord_url(url, soupify=True)
        return self.parse_show(webpage)

    def show_info(self, url):
        soup = self.get_streamlord_url(url, soupify=True)
        imdb_rating = soup.find(
            'p', attrs={'class': 'search-rating'}).text.strip()
        title = soup.find(
            'div', attrs={'class': 'movie-title'}).text.strip()
        section = soup.find('ul', attrs={'id': 'description-ul'})
        parts = [[sect.text.lower() for sect in sect.find_all(
            'li')] for sect in section.find_all('td')[:-1]]
        parts.append(['rating', imdb_rating])
        return (title, {p[0].lstrip().rstrip(): p[1].lstrip().rstrip() for p in parts})

    def table_header(self, table, header_name):
        table_length = len(table.split('\n')[0])
        available_space = table_length - 2
        spaces = self.space_make(available_space - len(header_name))
        og_s = "-"*available_space
        s1 = spaces[0]*" "
        s2 = spaces[1]*" "
        return f"+{og_s}+\n|{s1}{header_name}{s2}|"

    def parse_entries(self, entry):
        name = entry.find(
            'div', attrs={'class': 'movie-grid-title'}).find(text=True).lstrip().rstrip()
        year = entry.find(
            'span', attrs={'class': 'movie-grid-year'}).text.strip()
        url = entry.find('a', href=True).attrs['href']
        poster = entry.find('img').attrs.get('src')
        rating = entry.find(
            'p', attrs={'class': 'search-rating'}).text.strip()
        show_info = entry.select('.movie-grid-description')[0].text.strip()
        try:
            description, starring = show_info.split('\n\n\t\t\t\t\t\t\t\t')
            delimiter = '/' if '/' in starring else ','
            starring = [s.strip() for s in starring.split(delimiter)]
        except ValueError:
            description = ""
            starring = []
        obj = {
            'name': name,
            'url': url,
            'rating': float(rating),
            'poster': poster,
            'description': description,
            'starring': starring,
            'year': year
        }
        return obj

    def get_paginated_content(self, path_type, query_key, query_val):
        url = 'http://www.streamlord.com/{}.php?{}={}&page=1'.format(
            path_type, query_key, query_val)
        soup = self.get_streamlord_url(url, soupify=True)
        pagination = soup.select('#pagination > span > a')
        pag_bool = bool(pagination)
        movies = soup.find_all('div', attrs={'class': 'movie-grid'})
        if pag_bool:
            r_num = int(pagination[-1].text) + 1
        shows = list()
        for m in movies:
            obj = self.parse_entries(m)
            shows.append(obj)
        if pag_bool:
            for i in range(2, r_num):
                url = 'http://www.streamlord.com/{}.php?{}={}&page={}'.format(
                    path_type, query_key, query_val, i)
                soup = self.get_streamlord_url(url, soupify=True)
                movies = soup.find_all('div', attrs={'class': 'movie-grid'})
                for m in movies:
                    obj = self.parse_entries(m)
                    shows.append(obj)

        shows.sort(key=lambda x: x['name'])
        return shows
