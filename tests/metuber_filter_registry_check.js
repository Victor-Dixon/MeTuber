const fs = require("fs");
const vm = require("vm");

const code = fs.readFileSync("public/plugins/filter-registry.js", "utf8");
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(code, sandbox);

const registry = sandbox.window.MeTuberFilterRegistry;
if (!registry) throw new Error("registry missing");

const validation = registry.validate();
if (!validation.ok) {
  throw new Error("registry invalid: " + JSON.stringify(validation.errors));
}

const required = ["normal", "invert", "cartoon", "color", "sketch"];
for (const id of required) {
  if (!registry.get(id)) throw new Error(`missing plugin ${id}`);
  const filter = registry.getFilter(id, {});
  if (typeof filter !== "string" || filter.length < 1) {
    throw new Error(`bad filter for ${id}`);
  }
}

console.log(JSON.stringify({ ok: true, count: validation.count, required }, null, 2));
