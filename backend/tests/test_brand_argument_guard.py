"""No call drops a required brand, and none passes one where it is not taken.

ADR-172 made functions take the working brand, one at a time. Four times in
one week (2026-09-28 to 2026-10-03) a function gained a REQUIRED `brand_id`
and one caller was not updated: the Jinja override form, `GET
/recipients/{external_id}`, the approval seed's `summarise`, and — the other
way round — the events route passing a brand its service never took. Each
failed on every call, and nothing exercised it, so each was found by a
person clicking.

This reads the source with `ast` and fails at test time instead:

  * a call to a name whose EVERY definition requires `brand_id` must pass it;
  * a call passing `brand_id=` to a name NO definition accepts (nor `**kw`)
    is wrong too.

"Every" and "no" are what keep it quiet about shared names: SQLAlchemy's
`db.execute()` is not an approval action's `execute(..., brand_id)`, and a
rule that flagged it would be ignored within a week.
"""
import ast
import collections
import pathlib

BACKEND = pathlib.Path(__file__).resolve().parents[1]
ROOTS = [BACKEND / "app", BACKEND / "scripts", BACKEND / "main.py"]


def _sources():
    for root in ROOTS:
        for path in ([root] if root.is_file() else sorted(root.rglob("*.py"))):
            yield path, ast.parse(path.read_text(), str(path))


def _called_name(call: ast.Call):
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def _scan():
    requires = collections.defaultdict(list)   # name -> [positional index | "kw" | None]
    accepts = collections.defaultdict(list)    # name -> [bool]
    trees = list(_sources())
    for _path, tree in trees:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            a = node.args
            positional = a.posonlyargs + a.args
            required = positional[: len(positional) - len(a.defaults)] if a.defaults else positional
            index = next((i for i, x in enumerate(required) if x.arg == "brand_id"), None)
            kw_required = any(k.arg == "brand_id" and d is None
                              for k, d in zip(a.kwonlyargs, a.kw_defaults))
            requires[node.name].append(index if index is not None else ("kw" if kw_required else None))
            names = {x.arg for x in positional + a.kwonlyargs}
            accepts[node.name].append("brand_id" in names or a.kwarg is not None)
    return trees, requires, accepts


def test_no_call_omits_a_required_brand():
    trees, requires, _ = _scan()
    missing = []
    for path, tree in trees:
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call):
                continue
            name = _called_name(call)
            kinds = requires.get(name)
            if not kinds or any(k is None for k in kinds):
                continue  # some definition of this name does not require it
            if any(k.arg == "brand_id" or k.arg is None for k in call.keywords):
                continue  # passed by name, or through **kwargs
            if any(isinstance(arg, ast.Starred) for arg in call.args):
                continue
            positions = {k for k in kinds if k != "kw"}
            if positions and all(len(call.args) > p for p in positions):
                continue  # passed positionally
            missing.append(f"{path.relative_to(BACKEND)}:{call.lineno} {name}()")
    assert not missing, f"calls that drop a required brand_id: {missing}"


def test_no_call_passes_a_brand_where_none_is_taken():
    trees, _, accepts = _scan()
    wrong = []
    for path, tree in trees:
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call) or not any(k.arg == "brand_id" for k in call.keywords):
                continue
            name = _called_name(call)
            if name in accepts and not any(accepts[name]):
                wrong.append(f"{path.relative_to(BACKEND)}:{call.lineno} {name}(brand_id=...)")
    assert not wrong, f"calls passing brand_id to a function that cannot take it: {wrong}"
