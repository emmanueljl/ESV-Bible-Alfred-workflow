# encoding: utf-8
from urllib.parse import urlencode
from time import time
from hashlib import md5
import sys
import subprocess
import re
import os
import json

"""Alfred Script Filter to search the ESV Bible."""

API_KEY = '5974948d3baa3d1cabc4eb00e4099e3d785d43df'
API_URL = 'https://api.esv.org/v3/passage/text/'
API_OPTIONS = {
    'include-passage-references': 'false',
    'include-first-verse-numbers': 'false',
    'include-verse-numbers': 'false',
    'include-footnotes': 'false',
    'include-footnote-body': 'false',
    'include-short-copyright': 'false',
    'include-passage-horizontal-lines': 'false',
    'include-heading-horizontal-lines': 'false',
    'include-headings': 'false',
    'include-selahs': 'false',
    'indent-paragraphs': '0',
    'indent-poetry': 'false',
    'indent-poetry-lines': '0',
    'indent-declares': '0',
    'indent-psalm-doxology': '0'
}

# HTTP request headers
API_HEADERS = {
    'Accept': 'application/json',
    'Authorization': 'Token ' + API_KEY,
}


# Directory for this workflow's cache data
CACHEDIR = os.getenv('alfred_workflow_cache')
CACHE_MAXAGE = 86400 * 40  # 40 days


def log(s, *args):
    """Write message to Alfred's debugger.

    Args:
        s (basestring): Simple string or sprintf-style format.
        *args: Arguments to format string.

    """
    try:
        if isinstance(s, bytes):
            s = s.decode('utf-8')  # Decode bytes to string
    except AttributeError:
        pass
    if args:
        print(s % args, file=sys.stderr)
    else:
        print(s, file=sys.stderr)


class ESVError(Exception):
    """Base error class."""


class NotFound(ESVError):
    """Raised if no passage was found."""

    def __str__(self):
        """Error message."""
        return 'No passage found'


class APIError(ESVError):
    """Raised if API call fails."""


class Cache(object):
    """Cache results of API queries.

    Attributes:
        dirpath (str): Path to cache directory.

    """

    def __init__(self, dirpath):
        """Create a new cache.

        Args:
            dirpath (str): Directory to store cache files.

        """
        log('cache directory=%s', dirpath)
        self.dirpath = dirpath
        if dirpath is None:  # not being run from Alfred
            return

        # Alfred doesn't create the directory for you...
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        else:  # remove old cache files
            self.clean()

    def search(self, query):
        """Perform API query, using cached results if not expired.

        Args:
            query (str): Search string.

        Returns:
            Passage: Passage from API or cache.

        """
        cachepath = None
        if self.dirpath:
            cachepath = os.path.join(
                self.dirpath,
                md5(query.encode('utf-8')).hexdigest() + '.json'
            )

        # ------------------------------------------------------
        # Try to load data from cache
        if cachepath and os.path.exists(cachepath):
            # Expired cache files were deleted when `Cache` was created
            log('[cache] loading passage for "%s" from cache ...', query)
            with open(cachepath) as fp:
                data = json.load(fp)
                return Passage.from_response(data)

        # ------------------------------------------------------
        # Fetch data from API

        # Combine query and options into GET parameters
        params = dict(q=query.encode('utf-8'))
        params.update(API_OPTIONS)

        # Execute request
        data = fetch_url(API_URL, params, API_HEADERS)
        passage = Passage.from_response(data)

        if cachepath:  # Cache response
            with open(cachepath, 'wb') as fp:
                fp.write(json.dumps(data).encode('utf-8'))

        return passage

    def clean(self):
        """Remove expired cache files."""
        i = 0
        for fn in os.listdir(self.dirpath):
            p = os.path.join(self.dirpath, fn)
            if time() - os.stat(p).st_mtime > CACHE_MAXAGE:
                os.unlink(p)
                i += 1
        if i:
            log('[cache] deleted %d stale cache file(s)', i)


class Passage(object):
    """A Bible passage.

    Attributes:
        fulltext (unicode): Passage text as paragraphs
        ref (unicode): Canonical passage reference
        summary (unicode): Passage text on one line
        with_ref (unicode): Passage as paragraphs + reference

    """

    @classmethod
    def from_response(cls, data):
        """Create a `Passage` from API response.

        Args:
            data (dict): Decoded JSON API response.

        Returns:
            Passage: Passage parsed from API response.

        Raises:
            NotFound: Raised if ``data`` contains no passage(s).

        """
        if not data.get('canonical') or not data.get('passages'):
            raise NotFound()

        ref = data['canonical']
        s = data['passages'][0]
        summary = re.sub(r'\s+', ' ', s).strip()
        p = cls(ref, summary, s)
        log('---------- passage -----------')
        log('%s', p)
        log('---------- /passage ----------')
        return p

    def __init__(self, ref=u'', summary=u'', fulltext=u''):
        """Create new `Passage`."""
        self.ref = ref
        self.summary = summary
        self.fulltext = fulltext
        self.with_ref = u'{}\n\n({} ESV)'.format(fulltext.rstrip(), ref)

    def __str__(self):
        """Passage as formatted bytestring.

        Returns:
            str: Full text of passage with reference.
        """
        # return self.__unicode__().encode('utf-8')
        return self.__unicode__()

    def __unicode__(self):
        """Passage as formatted Unicode string.

        Returns:
            unicode: Full text of passage with reference.
        """
        return self.with_ref

    @property
    def item(self):
        """Alfred item `dict`.

        Returns:
            dict: Alfred item for JSON serialisation.

        """
        return {
            'title': self.ref,
            'subtitle': self.summary,
            'autocomplete': self.ref,
            'arg': self.with_ref,
            'valid': True,
            'text': {
                'largetype': self.with_ref,
                'copytext': self.with_ref,
            },
        }


def fetch_url(url, params, headers):
    """Fetch a URL using cURL and parse response as JSON.

    Args:
        url (str): Base URL without GET parameters.
        params (dict): GET parameters.
        headers (dict): HTTP headers.

    Returns:
        object: Deserialised HTTP JSON response.

    Raises:
        APIError: Raised if API returns an error.

    """
    # Encode GET parameters and add to URL
    qs = urlencode(params)
    url = url + '?' + qs

    # Build cURL command
    cmd = ['/usr/bin/curl', '-sSL', url]
    for k, v in headers.items():
        cmd.extend(['-H', '{}: {}'.format(k, v)])

    # Run command and parse response
    output = subprocess.check_output(cmd)
    log('---------- response -----------')
    log('%r', output)
    log('---------- /response ----------')
    data = json.loads(output)
    if 'detail' in data:  # 'detail' contains any API error message
        raise APIError(data['detail'])

    return data


def exit_with_error(title, err, tb=False):
    """Show an error message in Alfred and exit script.

    Args:
        title (unicode): Title of Alfred item.
        err (Exception): Error whose message to show as item subtitle.
        tb (bool, optional): If `True`, show a full traceback in Alfred's
            debugger.

    """
    # Log to debugger
    if tb:
        import traceback
        log(traceback.format_exc())
    else:
        log('ERROR: %s', err)

    # Send error message to Alfred
    output = {
        'items': [{'title': title, 'subtitle': str(err)}]
    }
    json.dump(output, sys.stdout)

    sys.exit(1)  # 1 indicates something went wrong


def main():
    """Run Script Filter."""
    log('.')  # Ensure real log starts on a new line

    # Fetch user query and decode to Unicode
    query = sys.argv[1]

    cache = Cache(CACHEDIR)
    try:
        passage = cache.search(query)
    except ESVError as err:
        exit_with_error(query, err, False)
    except Exception as err:
        exit_with_error(query, err, True)

    # Show passage in Alfred
    json.dump({'items': [passage.item]}, sys.stdout)


if __name__ == '__main__':
    start = time()
    main()
    log('------ %0.3fs ------', time() - start)
