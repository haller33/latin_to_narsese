const fs = require('fs');

const caminhoArquivo = process.argv[2];

if (!caminhoArquivo) {
    console.error("Erro: Informe o arquivo JSON.");
    process.exit(1);
}

fs.readFile(caminhoArquivo, 'utf8', (err, data) => {
    if (err) {
        console.error("Erro ao ler:", err);
        return;
    }

    const capitulos = JSON.parse(data);
    let todasAsPalavras = [];

    capitulos.forEach(item => {
        // 1. Primeiro transformamos em minúsculas e removemos quebras de linha
        const textoLimpo = item.paragrafo.toLowerCase().replace(/\n/g, " ");
        
        // 2. Dividimos por qualquer tipo de espaço em branco
        const blocos = textoLimpo.split(/\s+/);

        blocos.forEach(bloco => {
            // 3. O TRIM e a limpeza de pontuação por palavra
            // Removemos tudo que não for letra ou número (mantendo acentos)
            const palavra = bloco
                .trim()
                .replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, ""); // Limpa pontuação nas extremidades

            if (palavra.length > 0) {
                todasAsPalavras.push(palavra);
            }
        });
    });

    const totalPalavras = todasAsPalavras.length;
    const contagem = {};

    todasAsPalavras.forEach(p => {
        contagem[p] = (contagem[p] || 0) + 1;
    });

    const resultado = Object.keys(contagem)
        .map(p => ({
            palavra: p,
            percentual: ((contagem[p] / totalPalavras) * 100).toFixed(7)
        }))
        .sort((a, b) => b.percentual - a.percentual);

    resultado.forEach(item => {
        console.log(`${item.percentual} ${item.palavra}`);
    });
});
