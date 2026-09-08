from pathlib import Path
import json
from gzhseam.washer import wash,GzhCtx
text=Path("examples/presentation-output.html").read_text()
print(json.dumps({"html":text,"second_pass_same":wash(text).html==text,"restricted_html":wash("<p>Paragraph</p><a href='https://example.invalid'>Link text</a>",GzhCtx(whitelisted_tags={"p"})).html},indent=2))
