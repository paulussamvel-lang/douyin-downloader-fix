import json
from pathlib import Path
import tempfile
import unittest
from fix import build, fix_parser, fix_list_actions, LIST_ACTIONS_MARKER


PARSER = """function parse(href) {
      const url = new URL(href);
      const fromPath = url.pathname.match(VIDEO_PATH);
      if (fromPath) return fromPath[1];
      const modal = url.searchParams.get('modal_id') || url.searchParams.get('modalId');
      if (modal && /^\\d{5,}$/.test(modal)) return modal;
}
"""


class FixTests(unittest.TestCase):
    def test_list_actions_are_sticky_and_idempotent(self):
        css = '.dy-dl-list-actions { display: flex; }\n'
        fixed = fix_list_actions(css)
        self.assertIn('position: sticky;', fixed)
        self.assertIn('bottom: 0;', fixed)
        self.assertEqual(fixed.count(LIST_ACTIONS_MARKER), 1)
        self.assertEqual(fix_list_actions(fixed), fixed)

    def test_css_preserves_crlf(self):
        fixed = fix_list_actions('.dy-dl-list-actions { display: flex; }\r\n')
        self.assertNotIn('\n', fixed.replace('\r\n', ''))

    def test_unknown_stylesheet_rejected(self):
        with self.assertRaises(ValueError):
            fix_list_actions('.unrelated { display: block; }')

    def test_priority_and_idempotence(self):
        fixed = fix_parser(PARSER)
        self.assertLess(fixed.index('const modal'), fixed.index('const fromPath'))
        self.assertEqual(fix_parser(fixed), fixed)

    def test_crlf(self):
        fixed = fix_parser(PARSER.replace('\n', '\r\n'))
        self.assertNotIn('\n', fixed.replace('\r\n', ''))

    def test_unknown_parser_rejected(self):
        with self.assertRaises(ValueError):
            fix_parser('unrelated source')

    def test_build_preserves_original_and_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / 'original', Path(temp) / 'fixed'
            (source / 'lib').mkdir(parents=True)
            (source / 'lib/aweme-parse.js').write_text(PARSER)
            (source / 'content').mkdir()
            original_css = '.dy-dl-list-actions { display: flex; }\n'
            (source / 'content/content.css').write_text(original_css)
            manifest = {'manifest_version': 3, 'version': '1.1.1',
                        'permissions': ['downloads'], 'key': 'sample-key',
                        'update_url': 'https://example.com/update'}
            (source / 'manifest.json').write_text(json.dumps(manifest))
            (source / '_metadata').mkdir()
            build(source, output)
            result = json.loads((output / 'manifest.json').read_text())
            self.assertEqual(result['permissions'], manifest['permissions'])
            self.assertEqual(result['version'], '1.1.3')
            self.assertEqual((source / 'content/content.css').read_text(), original_css)
            self.assertIn(LIST_ACTIONS_MARKER, (output / 'content/content.css').read_text())
            self.assertNotIn('key', result)
            self.assertNotIn('update_url', result)
            self.assertFalse((output / '_metadata').exists())
            self.assertEqual((source / 'lib/aweme-parse.js').read_text(), PARSER)
            with self.assertRaises(ValueError):
                build(source, output)


if __name__ == '__main__':
    unittest.main()
