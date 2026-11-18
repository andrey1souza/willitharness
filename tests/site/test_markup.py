import markup


def test_tags_carry_names_attributes_and_lines():
    tags = markup.tags_of('<p id="a">x</p>\n<a href="#a">y</a>')
    assert [(tag.name, tag.closing, tag.line) for tag in tags] == [("p", False, 1), ("p", True, 1), ("a", False, 2), ("a", True, 2)], f"got {tags}"
    assert tags[0].attributes == {"id": "a"} and tags[2].attributes == {"href": "#a"}, f"got {tags}"


def test_text_blocks_skip_the_head_and_collapse_whitespace():
    html = "<html><head><title>T</title><style>p{}</style></head><body><h1>One\n  two</h1><p>Three <code>four</code>.</p></body></html>"
    assert markup.text_blocks(html) == ["One two", "Three four."], f"only body blocks count, got {markup.text_blocks(html)}"
    assert markup.text_blocks("<ul><li>a</li><li></li></ul>") == ["a"], "empty blocks are dropped"
    assert markup.text_blocks("<head><p>hidden</p></head><body><p>shown</p></body>") == ["shown"], "blocks in the head are not visible text"


def test_sentences_split_after_a_stop_and_unescape():
    assert markup.sentences_of("One. Two? Three!") == ["One.", "Two?", "Three!"], "stops end sentences"
    assert markup.sentences_of("a &amp; b. c") == ["a & b.", "c"], "entities are decoded"
