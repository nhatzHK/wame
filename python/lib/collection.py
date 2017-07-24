import sqlite3
import os
import random
import xkcd_helpers as XKCD

class Collection():
    """Collection manages local comics and ranking information."""

    def __init__(self, file_path):
        """Open a connection to a comic collection.

        :param file_path: The pathname of the program's sqlite3 database
            If the database does not exist, one will be created with
            appropriate schema information.
        """
        self.__comics_table = "comics"
        self.__words_table = "words"
        self.__word_weights_table = "word_weights"

        self.__con = self.__connect(file_path)

    def __del__(self):
        self.__con.commit()
        self.__con.close()

    def __connect(self, file_path):
        is_new_collection = not os.path.isfile(file_path)
        con = sqlite3.connect(file_path)

        if is_new_collection:  # Set up the table schemas.
            c = con.cursor()
            c.executescript("""
              CREATE TABLE {} (
                  id INTEGER PRIMARY KEY,
                  img_url TEXT NOT NULL,
                  title TEXT NOT NULL,
                  alt TEXT NOT NULL,
                  transcript TEXT NOT NULL
              );
              
              CREATE TABLE {} (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  word TEXT NOT NULL UNIQUE,
                  is_blacklisted INTEGER DEFAULT 0 CHECK(is_blacklisted in (0,1))
              );
              
              CREATE TABLE {} (
                  word_id INTEGER,
                  comic_id INTEGER,
                  weight INTEGER DEFAULT 1,
                  PRIMARY KEY (word_id, comic_id),
                  FOREIGN KEY (word_id) REFERENCES {}(id),
                  FOREIGN KEY (comic_id) REFERENCES {}(id)
              );
              """.format(self.__comics_table,
                         self.__words_table,
                         self.__word_weights_table, self.__words_table, self.__comics_table))
            con.commit()

        return con

    def add_comic(self, comic):
        """Add a comic to the collection.

        :param comic: A comic definition that should take the form,
            {
                "number": int,
                "img_url": string,
                "title": string,
                "alt": string,
                "transcript": string
            }
        """
        cursor = self.__con.cursor()
        cursor.execute('INSERT INTO {} (id, img_url, title, alt, transcript) VALUES (?,?,?,?,?)'
                       .format(self.__comics_table),
                       (comic["number"], comic["img_url"], comic["title"],
                        comic["alt"], comic["transcript"]))

        blob = '{} {} {}'.format(comic["title"], comic["alt"], comic["transcript"])
        blob = XKCD.removePunk(blob)

        words = list(blob.split(' '))
        words = [x for x in words if x and not (x == ' ')]

        for word in words:
            word = word.lower()
            # Add the word to the database if it isn't already there.

            cursor.execute('SELECT id FROM {} WHERE word = ?'
                           .format(self.__words_table), (word,))

            res = cursor.fetchone()
            word_id = 0
            if res is None:
                cursor.execute('INSERT INTO {} (word) VALUES (?)'
                               .format(self.__words_table), (word,))
                word_id = cursor.lastrowid
            else:
                word_id = res[0]

            # Update the weight of the word for this comic.

            cursor.execute('SELECT weight FROM {} WHERE word_id=? AND comic_id=?'
                           .format(self.__word_weights_table),
                           (word_id, comic["number"]))

            res = cursor.fetchone()

            if res is None:
                cursor.execute('INSERT INTO {} (word_id, comic_id) VALUES (?,?)'
                               .format(self.__word_weights_table),
                               (word_id, comic["number"]))
            else:
                cursor.execute('UPDATE {} SET weight=? WHERE word_id=? AND comic_id=?'
                               .format(self.__word_weights_table),
                               (res[0] + 1, word_id, comic["number"]))

        self.__con.commit()

    def add_to_blacklist(self, word):
        """Add a word to the list of blacklisted words.

        Blacklisted words are ignored in the phrase argument to self.get_from_phrase.

        :param word: A word to blacklist. This can be a new word or one that is already
            in the collection
        """
        cursor = self.__con.cursor()
        word = word.lower()
        try:
            cursor.execute('INSERT INTO {} (word, is_blacklisted) VALUES (?,?)'
                           .format(self.__words_table), (word, 1))
        except:
            cursor.execute('UPDATE {} SET is_blacklisted=? WHERE word=?'
                           .format(self.__words_table), (1, word))

        self.__con.commit()

    def get_comic(self, number):
        """Return a comic from the collection.

        See the self.add_comic documentation for the structure of the return type.

        :param number: An integer that uniquely identifies the comic
        :return: Either the comic matching the number or None if it is not in the collection
        """
        cursor = self.__con.cursor()
        cursor.execute('SELECT * FROM {} WHERE id = ?'
                       .format(self.__comics_table), (number,))
        return self.__row_to_comic(cursor.fetchone())

    def get_latest(self):
        """Return the latest comic from the collection.

        :return: The latest comic or None if the collection is empty
        """
        cursor = self.__con.cursor()
        cursor.execute('SELECT * FROM {} ORDER BY id DESC LIMIT 1'.format(self.__comics_table))
        return self.__row_to_comic(cursor.fetchone())

    def get_random(self):
        """Returns a random comic from the collection or None if it is empty."""
        cursor = self.__con.cursor()
        cursor.execute('SELECT * FROM {} ORDER BY RANDOM() LIMIT 1'.format(self.__comics_table))
        return self.__row_to_comic(cursor.fetchone())

    def __row_to_comic(self, row):
        """Turn a cursor's row result into a comic or None if the row is empty."""
        if row is None:
            return None
        return {
            "number": row[0],
            "img_url": row[1],
            "title": row[2],
            "alt": row[3],
            "transcript": row[4]
        }

    def get_from_phrase(self, phrase):
        """Use the phrase to find and return a comic that best fits the query.

        :param phrase: A list of words that describes a comic
        :return: Either the comic matching the number or None if it is not in the collection
        """
        cursor = self.__con.cursor()
        matched = dict()

        # Comics gain ranking if they contain words found in the phrase.
        for word in phrase:
            word = word.lower()

            cursor.execute('SELECT id FROM {} WHERE word=?'
                           .format(self.__words_table), (word,))
            id_row = cursor.fetchone()

            if id_row:  # Word exists. Find all comics that use it.
                cursor.execute('SELECT comic_id, weight FROM {} WHERE word_id=?'
                               .format(self.__word_weights_table), (id_row[0],))

                weights = dict()
                for row in cursor.fetchall():
                    weights[row[0]] = row[1]
                self.__combine_weights(matched, weights)

        if len(matched) > 0:
            max_score = matched \
                [max(matched, key=lambda x: matched[x]['score'])]['score']
            a = {x: matched[x] for x in matched if matched[x]['score'] == max_score}

            max_weight = a[max(a, key=lambda x: a[x]['weight'])]['weight']
            b = {x: a[x] for x in a if a[x]['weight'] == max_weight}

            return self.get_comic(random.choice(list(b.keys())))
        else:
            return None

    def __combine_weights(self, main, comic_weights):
        """Join comic weights into a main score group.

        :param main: The main collection of comics and their weights/scores
            {
                comic_number: {'weight': int, 'score': int}
            }
        :param comic_weights: Comics and their weights
            {
                comic_number: int <- This is the weight, not the score
            }
        """
        comic_nums = list(comic_weights.keys())
        for num in comic_nums:
            if num in main:
                main[num]['weight'] = main[num]['weight'] + comic_weights[num]
            else:
                main[num] = {'weight': comic_weights[num], 'score': 0}

        for num in list(set(comic_nums)):
            main[num]['score'] += 1
