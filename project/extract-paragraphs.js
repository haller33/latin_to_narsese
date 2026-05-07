// https://gist.github.com/haller33/c93bdcd6482a7bd94f41d458be00b08b
// Importa o módulo File System nativo do Node.js
const fs = require('fs');

// 1. Obtém o nome do arquivo do primeiro argumento da linha de comando
const fileName = process.argv[2];

// Verifica se um nome de arquivo foi fornecido
if (!fileName) {
    console.error("Erro: Por favor, forneça o caminho do arquivo como o primeiro argumento.");
    console.error("Uso: node extract_paragraphs.js <caminho/do/arquivo.txt>");
    process.exit(1);
}

// 2. Define a regex (com flags g, m, s)
// (.+?)[\!\?\.]\n\n
// ([\w\s\W]+?)[\!\?\.]\n\n/gm == 100%
// (.+?)[\!\?\.]\n\n/gms  === 100%
// g (global): Encontra todas as correspondências.
// m (multiline): Permite que ^ e $ casem com o início/fim de linha (não estritamente necessário aqui, mas boa prática).
// s (dotAll): Permite que o ponto (.) case com caracteres de quebra de linha (\n), essencial para parágrafos multilinhas.
const paragraphRegex = /(.+?)[\!\?\.]\n\n/gs;

/**
 * Lê o arquivo, aplica a regex e imprime os resultados.
 * * @param {string} filePath O caminho para o arquivo de texto.
 */
function extractParagraphs(filePath) {
    let fileContent;
    try {
        // Leitura síncrona do arquivo (mais simples para scripts de linha de comando)
        fileContent = fs.readFileSync(filePath, 'utf8');
    } catch (error) {
        console.error(`Erro ao ler o arquivo ${filePath}: ${error.message}`);
        return;
    }

    // Array para armazenar os objetos de resultado
    const results = [];
    let match;

    // 3. Loop de aplicação da regex (necessário devido à flag 'g')
    // O método exec() é usado em um loop com a flag 'g' para iterar sobre todas as correspondências.
    while ((match = paragraphRegex.exec(fileContent)) !== null) {
        // O grupo de captura do parágrafo é o primeiro item (índice 1)
        const paragraphText = match[1] ? match[1].trim() : '';

        if (paragraphText.length > 0) {
            results.push({
                index: results.length + 1,
                paragrafo: paragraphText
            });
        }
    }

    // 4. Imprime o array de objetos no console após a leitura
    console.log(JSON.stringify(results, null, 2));
}

// Executa a função principal
extractParagraphs(fileName);
