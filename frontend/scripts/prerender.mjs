import { mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'

const projectRoot = process.cwd()
const distributionDirectory = resolve(projectRoot, 'dist')
const clientHtmlPath = resolve(distributionDirectory, 'index.html')
const spaFallbackPath = resolve(distributionDirectory, 'spa.html')
const serverBundlePath = resolve(projectRoot, '.prerender/prerender.js')

const ROOT_PLACEHOLDER = '<div id="root"></div>'

const LANDING_PAGES = [
  {
    pathname: '/',
    language: 'pt-BR',
    outputPath: clientHtmlPath,
  },
  {
    pathname: '/pt-BR',
    language: 'pt-BR',
    outputPath: resolve(distributionDirectory, 'pt-BR/index.html'),
  },
  {
    pathname: '/en',
    language: 'en',
    outputPath: resolve(distributionDirectory, 'en/index.html'),
  },
]

async function prerenderLandingPages() {
  const { renderLandingPage } = await import(serverBundlePath)
  const clientHtml = await readFile(clientHtmlPath, 'utf8')

  if (!clientHtml.includes(ROOT_PLACEHOLDER)) {
    throw new Error('The Vite HTML output does not contain the application root placeholder.')
  }

  // Rotas privadas continuam usando um HTML vazio e são renderizadas no navegador.
  await writeFile(spaFallbackPath, clientHtml, 'utf8')

  for (const landingPage of LANDING_PAGES) {
    const renderedContent = await renderLandingPage(landingPage.pathname, landingPage.language)

    const localizedHtml = clientHtml
      .replace('<html lang="en">', `<html lang="${landingPage.language}">`)
      .replace(ROOT_PLACEHOLDER, `<div id="root">${renderedContent}</div>`)

    await mkdir(dirname(landingPage.outputPath), {
      recursive: true,
    })

    await writeFile(landingPage.outputPath, localizedHtml, 'utf8')
  }
}

try {
  await prerenderLandingPages()
} finally {
  await rm(resolve(projectRoot, '.prerender'), {
    force: true,
    recursive: true,
  })
}
