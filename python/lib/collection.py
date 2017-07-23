import sqlite3
import os

class Collection():
    """Collection manages local comics and ranking information."""

    def __init__(self, file_path):
        self.__comics_table = "comics"
        self.__words_table = "words"
        self.__word_weights_table = "word_weights"

        self.__con = self.__connect(file_path)
        self.__cursor = self.__con.cursor()

    def __del__(self):
        self.__con.commit()
        self.__con.close()

    def __connect(self, file_path):
        is_new_collection = not os.path.isfile(file_path)
        con = sqlite3.connect(file_path)

        if is_new_collection:  # Set up the table schemas.
            c = con.cursor()
            c.execute('CREATE TABLE {} (\
                        id INTEGER PRIMARY KEY,\
                        img_url TEXT NOT NULL,\
                        title TEXT NOT NULL,\
                        alt TEXT NOT NULL,\
                        transcript TEXT NOT NULL\
                        )'.format(self.__comics_table))

            c.execute('CREATE TABLE {} (\
                        id INTEGER PRIMARY KEY AUTOINCREMENT,\
                        word TEXT NOT NULL UNIQUE,\
                        is_blacklisted INTEGER DEFAULT 0 CHECK(is_blacklisted in (0,1))\
                        )'.format(self.__words_table))

            c.execute('CREATE TABLE {} (\
                        word_id INTEGER,\
                        comic_id INTEGER,\
                        weight INTEGER DEFAULT 1,\
                        PRIMARY KEY (word_id, comic_id),\
                        FOREIGN KEY (word_id) REFERENCES {}(id),\
                        FOREIGN KEY (comic_id) REFERENCES {}(id)\
                        )'.format(self.__word_weights_table, self.__words_table, self.__comics_table))
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
        self.__cursor.execute("INSERT INTO {} (id, img_url, title, alt, transcript) VALUES ({},'{}','{}','{}','{}')"
                              .format(self.__comics_table, comic["number"], comic["img_url"], comic["title"],
                                    comic["alt"], comic["transcript"]))

        phrase = '{} {} {}'.format(comic["title"], comic["alt"], comic["transcript"]).split(' ')

        for word in phrase:
            word = word.lower()
            # Add the word to the database if it isn't already there.

            self.__cursor.execute("SELECT id FROM {} WHERE word = '{}'".format(self.__words_table, word))

            res = self.__cursor.fetchone()
            word_id = 0
            if res is None:
                self.__cursor.execute("INSERT INTO {} (word) VALUES ('{}')".format(self.__words_table, word))
                word_id = self.__cursor.lastrowid
            else:
                word_id = res[0]

            # Update the weight of the word for this comic.

            self.__cursor.execute('SELECT weight FROM {} WHERE word_id={} AND comic_id={}'
                                  .format(self.__word_weights_table, word_id, comic["number"]))
            res = self.__cursor.fetchone()

            if res is None:
                self.__cursor.execute('INSERT INTO {} (word_id, comic_id) VALUES ({}, {})'
                                      .format(self.__word_weights_table, word_id, comic["number"]))
            else:
                self.__cursor.execute('UPDATE {} SET weight={} WHERE word_id={} AND comic_id={}'
                                      .format(self.__word_weights_table, res[0] + 1, word_id, comic["number"]))

        self.__con.commit()

    def add_to_blacklist(self, word):
        """Add a word to the list of blacklisted words.

        Blacklisted words are ignored in the phrase argument to self.get_from_phrase.

        :param word: A word to blacklist. This can be a new word or one that is already
            in the collection
        """
        word = word.lower()
        try:
            self.__cursor.execute("INSERT INTO {} (word, is_blacklisted) VALUES ('{}', {})"
                                  .format(self.__words_table, word, 1))
        except:
            self.__cursor.execute("UPDATE {} SET is_blacklisted={} WHERE word='{}'"
                                  .format(self.__words_table, 1, word))

        self.__con.commit()

    def get_comic(self, number):
        """Return a comic from the collection.

        See the self.add_comic documentation for the structure of the return type.

        :param number: An integer that uniquely identifies the comic
        :return: Either the comic matching the number or None if it is not in the collection
        """
        self.__cursor.execute('SELECT * FROM {} WHERE id = {}'.format(self.__comics_table, number))
        return self.__row_to_comic(self.__cursor.fetchone())

    def get_latest(self):
        """Return the latest comic from the collection.

        :return: The latest comic or None if the collection is empty
        """
        self.__cursor.execute('SELECT * FROM {} ORDER BY id DESC LIMIT 1'.format(self.__comics_table))
        return self.__row_to_comic(self.__cursor.fetchone())

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
        # comic's number => total word weight
        comics = dict()

        # Find the comics that mention words in phrase.
        for word in phrase:
            word = word.lower()
            self.__cursor.execute("SELECT id FROM {} WHERE word='{}' AND is_blacklisted=0"
                                  .format(self.__words_table, word))
            res = self.__cursor.fetchone()
            if res is None:
                continue

            self.__cursor.execute('SELECT comic_id, weight FROM {} WHERE word_id={}'
                                  .format(self.__word_weights_table, res[0]))
            for row in self.__cursor.fetchall():
                comic_id = row[0]
                weight = row[1]
                if comic_id in comics:
                    comics[comic_id] += weight
                else:
                    comics[comic_id] = weight

        # Get the comic that mentioned the most words.
        sorted_comics = sorted(comics.items(), reverse=True, key=lambda x: x[1])
        if len(sorted_comics) == 0:
            return None
        return self.get_comic(sorted_comics.pop()[0])
