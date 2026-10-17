const SOURCE_URL = 'https://github.com/crichalchemist/DigniFi';

/** The page footer on every route: DigniFi is AGPL-3.0-or-later, so it links to its source. */
export function SiteFooter() {
  return (
    <footer className="site-footer">
      <a href={SOURCE_URL}>Source code</a>
    </footer>
  );
}

export default SiteFooter;
