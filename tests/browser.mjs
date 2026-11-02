// One Chromium server per pytest worker; each client gets independent contexts.
import {chromium} from '../tools/render/node_modules/playwright/index.mjs';
export async function browser() {
  return process.env.KERF_TEST_BROWSER_WS
    ? chromium.connect(process.env.KERF_TEST_BROWSER_WS)
    : chromium.launch({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
}
if (process.argv[2] === '--serve') {
  const server = await chromium.launchServer({args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
  console.log(server.wsEndpoint());
  process.stdin.resume();
  process.stdin.on('end', async () => {await server.close(); process.exit(0);});
}
