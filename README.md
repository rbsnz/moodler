# moodler
Moodle resource scraper

# how to use

## clone the repo

```bash
git clone https://github.com/rbsnz/moodler
cd moodler
```

## install the requirements

```bash
pip install -r requirements.txt
```
or
```bash
python -m pip install -r requirements.txt
```

## run the script

```bash
python moodler.py -h host -t token -c courseId
```

`-h` you must provide a host name to connect to ex. `moodle.xxxxxx.com`\
`-t` you must provide your Moodle authentication token, you can find this as `MoodleSession` in your cookies\
`-c` you must provide a course ID, as seen in the URL `/course/view.php?id=xxxx`\
`-s` you may optionally provide a section ID to download only that section's resources
