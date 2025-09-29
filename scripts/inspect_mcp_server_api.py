import inspect
from mcp.server import FastMCP

m = FastMCP("debug-inspect")
attrs = dir(m)
print("Attributes on FastMCP:")
for a in attrs:
    print(a)

print("\nCallable attributes:")
for a in attrs:
    try:
        attr = getattr(m, a)
        if callable(attr):
            try:
                sig = str(inspect.signature(attr))
            except Exception:
                sig = "(signature unavailable)"
            print(f"- {a}{sig}")
    except Exception as e:
        print(f"- {a}: <error accessing attribute: {e}>")
