# Conlexa - Self-hosted conlanging tool

## Todo

- [ ] Dictionary
  - [x] Add word
  - [x] View and filter words
  - [ ] Search words
  - [x] Edit words
  - [x] Delete words
  - [ ] Constructed script support
    - [x] Support romanized vs scripted word entry
    - [ ] Display constructed script
- [ ] Notebook (grammar, translations)
- [ ] Languages
  - [ ] Add language and code
  - [ ] Language presentation and page
- [ ] IPA auto-guesser
- [ ] Conjugator




## How to

### Database

Database was made in PostgreSQL. There is an example sql script for creating the tables in this repo. You should then insert your language name and codes (example in the script) and you can start adding words through the interface. Alternatively, you should be able to import CWS-generated csv files from your db management program into table `words`.

Requirements:

```
pip install fastapi uvicorn psycopg2-binary
```

Change environment variables to your username and password in `run.sh` then run it. Open `localhost:8000` in your browser.


For now it works on Linux.