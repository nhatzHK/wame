import unittest
import uuid
import os
from collection import Collection

class TestCollection(unittest.TestCase):
    """Tests for the Collection class"""

    def test_construct_new_db(self):
        """The constructor should create a new database if one does not exist."""
        file_name = "./{}.sqlite".format(str(uuid.uuid4()))

        Collection(file_name)
        self.assertTrue(os.path.isfile(file_name))

        os.remove(file_name)

    def test_construct_existing_db(self):
        """The constructor should use the specified database if it exists."""
        file_name = "./{}.sqlite".format(str(uuid.uuid4()))

        def create_db():
            db = Collection(file_name)

        create_db()
        Collection(file_name)

        os.remove(file_name)

    def test_add_comic(self):
        """Adding valid comic structures should not throw an exception."""
        file_name = "./{}.sqlite".format(str(uuid.uuid4()))

        db = Collection(file_name)
        db.add_comic({
            "number":     4,
            "img_url":    "https://www.google.com",
            "title":      "A Title",
            "alt":        "Some alt-text",
            "transcript": "Hoi hoi"
        })

        os.remove(file_name)

    def test_get_comic_by_number(self):
        """get_comic should retrieve a comic with a matching id/number."""
        file_name = "./{}.sqlite".format(str(uuid.uuid4()))
        comic_number = 4

        db = Collection(file_name)
        db.add_comic({
            "number": comic_number,
            "img_url": "https://www.google.com",
            "title": "A Title",
            "alt": "Some alt-text",
            "transcript": "Hoi hoi"
        })

        comic = db.get_comic(comic_number)
        self.assertIsNotNone(comic)
        os.remove(file_name)

    def test_get_latest(self):
        file_name = "./{}.sqlite".format(str(uuid.uuid4()))
        db = Collection(file_name)
        latest = 10

        for num in range(1, latest + 1):
            db.add_comic({
                "number": num,
                "img_url": "https://www.google.com",
                "title": "A Title",
                "alt": "Some alt-text",
                "transcript": "Hoi hoi"
            })
        db.add_comic({
            "number": 0,
            "img_url": "https://www.google.com",
            "title": "A Title",
            "alt": "Some alt-text",
            "transcript": "Hoi hoi"
        })

        comic = db.get_latest()
        self.assertEqual(comic["number"], latest)

        os.remove(file_name)

    def test_get_from_phrase(self):
        """get_from_phrase should return the comic that is most similar to the phrase."""
        file_name = "./{}.sqlite".format(str(uuid.uuid4()))

        db = Collection(file_name)
        db.add_comic({
            "number": 1,
            "img_url": "https://www.google.com",
            "title": "A Title",
            "alt": "Some alt-text",
            "transcript": "Hoi hoi"
        })
        db.add_comic({
            "number": 2,
            "img_url": "https://www.google.com",
            "title": "A Title",
            "alt": "Some alt-text",
            "transcript": "Hoi hoi, mijn vrienden. Zei ik hoi? Hoi."
        })

        comic = db.get_from_phrase(["The", "hoi", "one"])
        self.assertIsNotNone(comic)
        self.assertIs(comic["number"], 2)
        os.remove(file_name)

    def test_add_to_blacklist_new(self):
        """Adding a new word as blacklisted should not throw an exception."""
        file_name = "./{}.sqlite".format(str(uuid.uuid4()))

        db = Collection(file_name)
        db.add_to_blacklist('and')

        os.remove(file_name)

    def test_add_to_blacklist_replace(self):
        """Changing the blacklisted status of an existing word should not throw an exception."""
        file_name = "./{}.sqlite".format(str(uuid.uuid4()))
        word = 'hoi'

        db = Collection(file_name)
        db.add_comic({
            "number": 1,
            "img_url": "https://www.google.com",
            "title": "A Title",
            "alt": "Some alt-text",
            "transcript": "Hoi " + word
        })
        db.add_to_blacklist(word)

        os.remove(file_name)

if __name__ == '__main__':
    unittest.main()