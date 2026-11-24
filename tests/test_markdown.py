from flutter_web_seo import markdown_lite as md


def test_blocks():
    out = md.render("## Title\n\nHello **bold** and *it* and `x<y`.\n\n- a\n- b\n\n1. one\n2. two")
    assert "<h2>Title</h2>" in out
    assert "<strong>bold</strong>" in out and "<em>it</em>" in out
    assert "<code>x&lt;y</code>" in out
    assert "<ul><li>a</li><li>b</li></ul>" in out
    assert "<ol><li>one</li><li>two</li></ol>" in out


def test_html_is_escaped():
    assert "<script>" not in md.render("<script>alert(1)</script>")


def test_links_only_safe_schemes():
    assert '<a href="https://x.dev/a">t</a>' in md.render("[t](https://x.dev/a)")
    assert '<a href="/tools">t</a>' in md.render("[t](/tools)")
    out = md.render("[t](javascript:alert(1))")
    assert "href" not in out and "t" in out


def test_plain():
    assert md.plain("**Hi** [there](/x) `code`\n- item") == "Hi there code item"
