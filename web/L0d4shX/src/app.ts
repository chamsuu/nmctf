import { Application } from "https://deno.land/x/oak/mod.ts";
import _ from "npm:lodash@4.17.23";

const template = Deno.readTextFileSync("./views/index.html");

const BLOCKED = ["Deno", "constructor", "Function", "eval", "readTextFileSync","+"];

function waf(body) {
  const str = JSON.stringify(body);
  for (const word of BLOCKED) {
    if (str.includes(word)) {
      return `Blocked: "${word}" detected in request`;
    }
  }
}

const app = new Application();
app.use(async (ctx) => {
  const body = ctx.request.body;
  const opts = await body.json();
  const blocked = waf(opts);
  if (blocked) {
    ctx.response.status = 403;
    ctx.response.body = blocked;
    return;
  }
  const fn = _.template(template, opts);
  ctx.response.body = fn({});
});
await app.listen({ port: 8000 });
