import unittest

import commonmark
from recipemd._vendor.commonmark_extensions.tables import ParserWithTables, RendererWithTables
from recipemd._vendor.commonmark_extensions.plaintext import PlainTextRenderer


class GithubFlavoredTablesTests(unittest.TestCase):
    """Test against Github-flavored Markdown defined at
    https://github.github.com/gfm/#tables-extension-
    Unfortunately many of the tests --- especially tests
    for invalid table markup --- are failing."""


    def assertRender(self, markdown, expected):
        parser = ParserWithTables(options={"multiline_table_cells": False})
        ast = parser.parse(markdown)
        html = RendererWithTables().render(ast)
        html = html.rstrip()
        self.assertEqual(html, expected)


    def test_simple(self):
        self.assertRender(
"""| foo | bar |
| --- | --- |
| baz | bim |""",

"""<table>
<thead>
<tr>
<th>foo</th>
<th>bar</th>
</tr>
</thead>
<tbody>
<tr>
<td>baz</td>
<td>bim</td>
</tr>
</tbody>
</table>"""            
        )


    def test_alignment(self):
        self.assertRender(
"""| abc | defghi |
:-: | -----------:
bar | baz""",

"""<table>
<thead>
<tr>
<th align="center">abc</th>
<th align="right">defghi</th>
</tr>
</thead>
<tbody>
<tr>
<td align="center">bar</td>
<td align="right">baz</td>
</tr>
</tbody>
</table>""")


    def test_escapes(self):
        self.assertRender(
"""| f\|oo  |
| ------ |
| b `\|` az |
| b **\|** im |""",

"""<table>
<thead>
<tr>
<th>f|oo</th>
</tr>
</thead>
<tbody>
<tr>
<td>b <code>|</code> az</td>
</tr>
<tr>
<td>b <strong>|</strong> im</td>
</tr>
</tbody>
</table>""")


    def test_break(self):
        self.assertRender(
"""| abc | def |
| --- | --- |
| bar | baz |
> bar""",

"""<table>
<thead>
<tr>
<th>abc</th>
<th>def</th>
</tr>
</thead>
<tbody>
<tr>
<td>bar</td>
<td>baz</td>
</tr>
</tbody>
</table>

<blockquote>
<p>bar</p>
</blockquote>""")


    def test_break2(self):
        self.assertRender(
"""| abc | def |
| --- | --- |
| bar | baz |
bar""",

"""<table>
<thead>
<tr>
<th>abc</th>
<th>def</th>
</tr>
</thead>
<tbody>
<tr>
<td>bar</td>
<td>baz</td>
</tr>
<tr>
<td>bar</td>
<td></td>
</tr>
</tbody>
</table>
<p>bar</p>""")


    def test_header_cells_count_matches_delimiter_row(self):
        self.assertRender(
"""| abc | def |
| --- |
| bar |""",

"""<p>| abc | def |
| --- |
| bar |</p>""")


    def test_cols_need_not_match(self):
        self.assertRender(
"""| abc | def |
| --- | --- |
| bar |
| bar | baz | boo |""",

"""<table>
<thead>
<tr>
<th>abc</th>
<th>def</th>
</tr>
</thead>
<tbody>
<tr>
<td>bar</td>
<td></td>
</tr>
<tr>
<td>bar</td>
<td>baz</td>
</tr>
</tbody>
</table>""")


    def test_no_tbody_if_empty(self):
        self.assertRender(
"""| abc | def |
| --- | --- |""",

"""<table>
<thead>
<tr>
<th>abc</th>
<th>def</th>
</tr>
</thead>
</table>""")

            
class MultilineTablesTests(unittest.TestCase):
    """Test the multiline cell mode."""


    def assertRender(self, markdown, expected):
        parser = ParserWithTables()
        ast = parser.parse(markdown)
        html = RendererWithTables().render(ast)
        html = html.rstrip()
        self.assertEqual(html, expected)


    def test_simple(self):
        self.assertRender(
"""| foo | bar |
| === | === |
| baz | bim |
| baz | bim |""",

"""<table>
<thead>
<tr>
<th>foo</th>
<th>bar</th>
</tr>
</thead>
<tbody>
<tr>
<td><p>baz
baz</p>
</td>
<td><p>bim
bim</p>
</td>
</tr>
</tbody>
</table>"""            
        )
        

class PlainTextRendererTests(unittest.TestCase):
    """Test the PlainTextRenderer cell mode."""


    def assertRender(self, markdown, expected):
        parser = commonmark.Parser()
        ast = parser.parse(markdown)
        text = PlainTextRenderer().render(ast).rstrip()
        self.assertEqual(text, expected)


    def test_simple(self):
        self.assertRender("""Hello""", """Hello""")

    def test_heading(self):
        self.assertRender("""# Heading *Formatting*""", """Heading *Formatting*\n####################""")

if __name__ == '__main__':
    unittest.main()