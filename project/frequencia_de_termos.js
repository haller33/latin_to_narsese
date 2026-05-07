const fs = require('fs');

// Pega o argumento passado no terminal. 
// O índice 0 é o Node, o 1 é o script, o 2 é o seu arquivo.
const caminhoArquivo = process.argv[2];

if (!caminhoArquivo) {
    console.error("Erro: Por favor, informe o nome do arquivo JSON.");
    console.log("Uso: node contador.js seu_arquivo.json");
    process.exit(1);
}

fs.readFile(caminhoArquivo, 'utf8', (err, data) => {
    if (err) {
        console.error("Erro ao ler o arquivo:", err);
        return;
    }

    const capitulos = JSON.parse(data);
    let todasAsPalavras = [];

    // 2. Extrair e limpar o texto
    capitulos.forEach(item => {
        // Remove pontuação básica e transforma em minúsculas para não diferenciar "O" de "o"
        const palavras = item.paragrafo
            .toLowerCase()
            .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()\"—]/g, "") // Remove pontuação
            .replace(/\n/g, " ") // Remove quebras de linha
            .split(/\s+/) // Divide por espaços
            .filter(p => p.length > 0); // Remove entradas vazias
        
        todasAsPalavras.push(...palavras);
    });

    const totalPalavras = todasAsPalavras.length;
    const contagem = {};

    // 3. Contar ocorrências
    todasAsPalavras.forEach(palavra => {
        contagem[palavra] = (contagem[palavra] || 0) + 1;
    });

    // 4. Calcular percentual e formatar o output
    // Transformamos em array para ordenar (opcional, aqui está da mais comum para a menos)
    const resultado = Object.keys(contagem)
        .map(palavra => {
            const percentual = (contagem[palavra] / totalPalavras) * 100;
            return {
                palavra: palavra,
                percentual: percentual.toFixed(7) // 7 casas decimais
            };
        })
        .sort((a, b) => b.percentual - a.percentual);

    // 5. Output simples conforme solicitado
    resultado.forEach(item => {
        console.log(`${item.percentual} ${item.palavra}`);
    });
});
