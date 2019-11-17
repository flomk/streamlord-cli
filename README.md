# streamlord-cli
CLI for [streamlord](http://www.streamlord.com/)

# Install

    python3 -m venv venv
    source venv/bin/activate
    pip install --no-cache-dir -r requirements.txt

# Usage
    usage: streamlord-cli [-h] [-j] [-c CAPTIONS] [-i INFO] [-g GENRE]
                        [--sort-by {rating,year}] [--list-genres] [-t] [-m]
                        [-l LETTER | -s SHOW | -e EPISODE | -f FILM | -w WEBPAGE]

    CLI for streamlord.com

    optional arguments:
    -h, --help            show this help message and exit
    -j, --json            return json response
    -c CAPTIONS, --captions CAPTIONS
                            include captions
    -i INFO, --info INFO  show info
    -g GENRE, --genre GENRE
    --sort-by {rating,year}
    --list-genres         list all categories
    -l LETTER, --letter LETTER
                            Get all shows that start with a letter
    -s SHOW, --show SHOW  Get all episodes of T.V. show
    -e EPISODE, --episode EPISODE
                            Get the source of a T.V. episode
    -f FILM, --film FILM  Get the source of a movie
    -w WEBPAGE, --webpage WEBPAGE
                            Get the html of a streamlord url

    Type of media:
    -t, --tv
    -m, --movie

# TODO
- [ ] Refactor code