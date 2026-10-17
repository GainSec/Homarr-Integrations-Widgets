import json,re,threading,time,urllib.parse,urllib.request
from configure_widget import checked_url

def text(value, limit=512):
    return value[:limit] if isinstance(value, str) else ''


def workbench_metadata(value):
    return {
        'slug': text(value.get('slug'), 128),
        'title': text(value.get('title'), 256),
        'description': text(value.get('description')),
        'tags': [text(tag, 80) for tag in (value.get('tags') or [])[:16]],
        'created_at': text(value.get('created_at'), 64),
        'updated_at': text(value.get('updated_at'), 64),
    }


def object_metadata(value):
    return {
        'id': text(value.get('id'), 128),
        'kind': text(value.get('kind'), 64),
        'title': text(value.get('title'), 256),
        'filename': text(value.get('filename'), 256),
        'created_at': text(value.get('created_at'), 64),
        'updated_at': text(value.get('updated_at'), 64),
        'archived': value.get('archived') is True,
    }


def validate_slug(slug, known_slugs):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', slug) or slug not in known_slugs:
        raise ValueError('Unknown workbench')
    return slug


class ArcticClient:
    origin = 'https://app.example.net'

    def __init__(self, origin="https://app.example.net"):
        self.origin = checked_url(origin)
        self.cache = {}
        self.lock = threading.RLock()

    def read(self, path, mapper):
        with self.lock:
            cached = self.cache.get(path)
            if cached and time.monotonic() < cached[0]:
                return cached[1]
            with urllib.request.urlopen(self.origin + path, timeout=10) as response:
                body = response.read(2 * 1024 * 1024 + 1)
            if len(body) > 2 * 1024 * 1024:
                raise RuntimeError('Metadata response too large')
            raw = json.loads(body)
            if not isinstance(raw, list):
                raise RuntimeError('Unexpected metadata response')
            data = [mapper(value) for value in raw if isinstance(value, dict)]
            data.sort(key=lambda item: item.get('updated_at') or item.get('created_at') or '', reverse=True)
            data = data[:500]
            if len(self.cache) >= 128:
                self.cache.clear()
            self.cache[path] = (time.monotonic() + 30, data)
            return data

    def workbenches(self):
        return self.read('/api/workbenches', workbench_metadata)

    def objects(self, slug):
        validate_slug(slug, {value['slug'] for value in self.workbenches()})
        return self.read('/api/workbenches/' + urllib.parse.quote(slug, safe='') + '/objects', object_metadata)
