CREATE TABLE IF NOT EXISTS words
(
    id SERIAL PRIMARY KEY,
    word text NOT NULL,
    word_scripted text,
    def_en text,
    pos VARCHAR(10),
    class text,
    etymology text,
    ipa text,
    language_code VARCHAR(10) NOT NULL,
    tags text[],
    example text
)

CREATE TABLE IF NOT EXISTS parts_of_speech
(
    code VARCHAR(10) PRIMARY KEY,
    name_en text NOT NULL
)

CREATE TABLE IF NOT EXISTS langs
(
    code VARCHAR(10) PRIMARY KEY,
    name_en text NOT NULL,
    name_native text
)


ALTER TABLE IF EXISTS words
    OWNER to conlexa; -- db username here

ALTER TABLE IF EXISTS parts_of_speech
    OWNER to conlexa; -- db username here

ALTER TABLE IF EXISTS langs
    OWNER to conlexa; -- db username here


INSERT INTO parts_of_speech (code, name_en) VALUES
('N', 'noun'),
('V', 'verb'),
('ADJ', 'adjective'),
('ADV', 'adverb'),
('ADP', 'adposition'),
('P', 'pronoun'),
('PTC', 'particle'),
('NUM', 'numeral');