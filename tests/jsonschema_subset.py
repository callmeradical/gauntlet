"""A standard-library JSON Schema (2020-12) validator for the keywords the Agent Plugins schemas use.

validate(instance, schema) returns a list of error strings (empty when valid). Any keyword
outside SUPPORTED or ANNOTATIONS raises NotImplementedError, so nothing is silently ignored.
"""

import re

ANNOTATIONS = {"$schema", "$id", "$defs", "title", "description"}
SUPPORTED = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "propertyNames",
    "items",
    "const",
    "enum",
    "minLength",
    "maxLength",
    "pattern",
    "$ref",
    "oneOf",
    "not",
}

_SCHEMA_VALUED = {"additionalProperties", "propertyNames", "items", "not"}


def unsupported_keywords(schema):
    """Keywords used anywhere in `schema` that this validator does not implement."""
    found = set()

    def walk(node):
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key not in SUPPORTED and key not in ANNOTATIONS:
                found.add(key)
            if key in ("properties", "$defs"):
                for sub in value.values():
                    walk(sub)
            elif key == "oneOf":
                for sub in value:
                    walk(sub)
            elif key in _SCHEMA_VALUED:
                walk(value)

    walk(schema)
    return found


def _ecma_pattern(pattern):
    """Translate ECMA-262 `$` (end of input only) to Python's `\\Z`; Python's `$` also matches before a final newline."""
    out, i, in_class = [], 0, False
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\":
            out.append(pattern[i : i + 2])
            i += 2
            continue
        if ch == "[":
            in_class = True
        elif ch == "]":
            in_class = False
        elif ch == "$" and not in_class:
            ch = r"\Z"
        out.append(ch)
        i += 1
    return "".join(out)


def _is_type(value, name):
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if isinstance(value, bool):
        return False
    if name == "integer":
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float))
    raise NotImplementedError("type %r" % name)


def _resolve(root, ref):
    if not ref.startswith("#/"):
        raise NotImplementedError("only local $ref is supported: %r" % ref)
    node = root
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def validate(instance, schema, root=None, path="$"):
    """Errors found validating `instance` against `schema`, each prefixed with its JSON path."""
    root = schema if root is None else root
    if schema is True:
        return []
    if schema is False:
        return ["%s: not allowed" % path]
    unknown = set(schema) - SUPPORTED - ANNOTATIONS
    if unknown:
        raise NotImplementedError("unsupported keywords at %s: %s" % (path, sorted(unknown)))

    errors = []
    if "$ref" in schema:
        errors += validate(instance, _resolve(root, schema["$ref"]), root, path)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(instance, t) for t in types):
            return errors + ["%s: expected %s" % (path, " or ".join(types))]
    if "const" in schema and instance != schema["const"]:
        errors.append("%s: must equal %r" % (path, schema["const"]))
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: must be one of %r" % (path, schema["enum"]))
    if "not" in schema and not validate(instance, schema["not"], root, path):
        errors.append("%s: must not match %r" % (path, schema["not"]))
    if "oneOf" in schema:
        matches = sum(1 for sub in schema["oneOf"] if not validate(instance, sub, root, path))
        if matches != 1:
            errors.append("%s: must match exactly one schema in oneOf (matched %d)" % (path, matches))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: shorter than %d" % (path, schema["minLength"]))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("%s: longer than %d" % (path, schema["maxLength"]))
        if "pattern" in schema and not re.search(_ecma_pattern(schema["pattern"]), instance):
            errors.append("%s: does not match %r" % (path, schema["pattern"]))

    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors += validate(item, schema["items"], root, "%s[%d]" % (path, i))

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append("%s: missing required property %r" % (path, key))
        properties = schema.get("properties", {})
        for key, value in instance.items():
            where = "%s.%s" % (path, key)
            if "propertyNames" in schema:
                errors += ["%s (property name)" % e for e in validate(key, schema["propertyNames"], root, where)]
            if key in properties:
                errors += validate(value, properties[key], root, where)
            elif "additionalProperties" in schema:
                errors += validate(value, schema["additionalProperties"], root, where)
    return errors
