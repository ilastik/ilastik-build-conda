import sys
import re


def format_version_string(version_tag):
    parts = version_tag.split(".")
    assert len(parts) == 3, parts
    return f'({parts[0]}, {parts[1]}, "{parts[2]}")'


if __name__ == "__main__":
    assert len(sys.argv) == 3, sys.argv
    _, version_file, version_tag = sys.argv
    version_tag = format_version_string(version_tag)

    with open(version_file, "r") as f:
        v_content = f.read()

    r_pattern = "^(__version_info__ = )(\(.*\))$"
    v_content_new = re.sub(
        pattern=r_pattern,
        repl=f"\\1{version_tag}",
        string=v_content,
        flags=re.MULTILINE,
    )

    with open(version_file, "w") as f:
        f.write(v_content_new)
