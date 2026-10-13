# jessevriend.com

A plain, one-page personal site. The words live in `content/` as small JSON files and `build.py` turns them into `dist/`. You edit them at **/admin** (Sveltia CMS); saving there commits to this repo, and the push rebuilds and deploys the site.

## Editing

1. Go to `/admin` on the site.
2. Choose **Sign In Using Access Token** and paste a GitHub fine-grained token that has *Contents: read and write* on this repository only (create one at github.com/settings/personal-access-tokens). The token stays in your browser. (The **Sign In with GitHub** button needs an OAuth server this site does not have, so it opens a page that tells you to use the token instead.)
3. Edit the Home page, the Being and Becoming section, Apps and projects, One-pagers and Writing. Sections with nothing in them are left out of the page. **Save** publishes the change in about a minute.

One-pager PDFs you upload go to `static/pagers/`; other uploads go to `static/uploads/`.

## Layout

- `content/site.json`, `content/bb.json`: home page text and the Being and Becoming section
- `content/projects/`, `content/pagers/`, `content/writing/`: one file per card or piece
- `style.css`: the look (cream, serif, rounded cards)
- `admin/`: the editor (`config.yml` says what can be edited; `sveltia-cms.js` is a pinned copy of Sveltia CMS 0.235.1, MIT)
- `build.py`, `tests/`: the build and its tests (`python -m unittest discover -s tests`)

The site stays out of search engines until "Let search engines find this site" is ticked on the Home page.
