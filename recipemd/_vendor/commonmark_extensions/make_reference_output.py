import codecs
import os.path
import re
import sys

import commonmark
import commonmark.render.html
import recipemd._vendor.commonmark_extensions.plaintext

def get_tests():
    if not os.path.exists("spec.txt"):
        print("Download the latest CommonMark spec.txt, e.g.:")
        print("wget https://raw.githubusercontent.com/jgm/CommonMark/master/spec.txt")
        sys.exit(0)

    # Read the spec.txt file and normalize line endings (I'm copying from CommonMark-py here).
    with codecs.open("spec.txt", encoding="utf-8") as f:
        spec = "".join(f.readlines())
    spec = spec.replace("→", "\t")

    # Chop off part that indicates end of tests.
    spec = re.sub(re.compile("^<!-- END TESTS -->(.|[\n])*", flags=re.M), '', spec)

    # Find all examples embedded in the spec, which serve as unit tests. I'm copying from:
    # https://github.com/rtfd/CommonMark-py/blob/master/CommonMark/tests/run_spec_tests.py
    tests = re.findall(
        re.compile(
            "^`{32} example\n"
            "([\s\S]*?)^\.\n([\s\S]*?)"
            "^`{32}$"
            "|^#{1,6} *(.*)$",
            re.M),
        spec)

    # Re-form into Python dicts.
    current_section = [None] # wrap in object to make closure
    def is_section_name(match):
        if not match[2] == "":
            current_section[0] = match[2]
            return True
        return False
    return [
        {
            'markdown': match[0],
            'html': match[1],
            'section': current_section[0],
            'number': example_number,
        }
        for example_number, match
        in enumerate(tests)
        if not is_section_name(match)
    ]

def run_tests():
    test_output = []

    parser = commonmark.Parser()

    for test in get_tests():
        # Render as text and output.
        # Since we don't have reference output, we'll make our own and
        # just track if it changes.

        renderer = recipemd._vendor.commonmark_extensions.plaintext.PlainTextRenderer()
        ast = parser.parse(test['markdown'])

        heading = "TEST (%s)" % test['section']
        print(heading)
        print("=" * len(heading))
        print()
        print("markdown:")
        print(test['markdown'])
        print("HTML:")
        print(test['html'])
        print("output:")

        try:
            output = renderer.render(ast)
        except recipemd._vendor.commonmark_extensions.plaintext.RawHtmlNotAllowed:
            print("[raw HTML is not permitted in plain text output]\n")
        else:
            print(output)

        # Render as CommonMark, then re-parse it, render that to
        # HTML, and see if the HTML matches the reference HTML.
        cm = recipemd._vendor.commonmark_extensions.plaintext.CommonMarkToCommonMarkRenderer().render(ast)
        ast = parser.parse(cm)
        html = commonmark.render.html.HtmlRenderer().render(ast)
        if html != test['html']:
            # This is an error. Round-tripping didn't work.
            print("Round-tripping CommonMark failed. It generated:")
            print(cm)


run_tests()

