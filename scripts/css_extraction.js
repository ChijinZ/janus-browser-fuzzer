const css = require('@webref/css');
const fs = require('fs');

async function main() {
    let dict = {}
    const parsedFiles = await css.listAll();
    for (const [shortname, data] of Object.entries(parsedFiles)) {
        for (const property of data.properties) {
            console.assert("name" in property);
            try {
                dict[property["name"]] = property
            } catch {
                // one of the few value definitions that cannot yet be parsed by CSSTree
            }
        }
    }
    let css_write_stream = fs.createWriteStream("./css_desc.json");
    css_write_stream.write(JSON.stringify(dict));

}

let _ = main();