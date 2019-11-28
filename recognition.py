import face_recognition
import requests
from io import BytesIO
import time


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' %
                  (method.__name__, (te - ts) * 1000))
        return result

    return timed


@timeit
def is_same_person(known_url, unknown_url):
    try:
        known_bytes = BytesIO(requests.get(known_url).content)
        unknown_bytes = BytesIO(requests.get(unknown_url).content)

        known_image = face_recognition.load_image_file(known_bytes)
        unknown_image = face_recognition.load_image_file(unknown_bytes)

        known_encoding = face_recognition.face_encodings(known_image)[0]
        unknown_encoding = face_recognition.face_encodings(unknown_image)[0]

        return face_recognition.compare_faces(
            [known_encoding], unknown_encoding)[0]

    except:
        return False
