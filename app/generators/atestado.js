/**
 * Gerador de Atestado Médico — Node.js com docx-js
 *
 * Uso: node atestado.js <json_path> <output_path>
 */

const fs = require("fs");
const path = require("path");
const {
  Document,
  Packer,
  Paragraph,
  TextRun,
  ImageRun,
  Header,
  Footer,
  AlignmentType,
  BorderStyle,
} = require("docx");

const ASSETS_DIR = path.join(__dirname, "..", "assets");
const GREEN = "2E5D34";

// Números por extenso
const EXTENSO = {
  1: "um", 2: "dois", 3: "três", 4: "quatro", 5: "cinco",
  6: "seis", 7: "sete", 8: "oito", 9: "nove", 10: "dez",
  11: "onze", 12: "doze", 13: "treze", 14: "quatorze", 15: "quinze",
  16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove", 20: "vinte",
  21: "vinte e um", 22: "vinte e dois", 23: "vinte e três", 24: "vinte e quatro",
  25: "vinte e cinco", 26: "vinte e seis", 27: "vinte e sete", 28: "vinte e oito",
  29: "vinte e nove", 30: "trinta"
};

function inferGenero(nome) {
  // Tenta inferir gênero pelo primeiro nome
  const primeiro = (nome || "").trim().split(/\s+/)[0].toUpperCase();
  // Nomes femininos comuns terminados em A (com exceções)
  const masculinos = ["JOSÁ", "LUCA", "NATANATA"];
  if (masculinos.includes(primeiro)) return "m";
  if (primeiro.endsWith("A") || primeiro.endsWith("E") && !["JOSÉ", "Felipe", "HENRIQUE", "JORGE"].includes(primeiro)) {
    // Heurística: terminado em A geralmente feminino
    if (primeiro.endsWith("A")) return "f";
  }
  // Default: incerto
  return "i";
}

async function gerarAtestado(dados, outputPath) {
  const { nome_paciente, data, dias, cid, diagnostico } = dados;

  const logoData = fs.readFileSync(path.join(ASSETS_DIR, "LOGO_FISIOMED.png"));
  const rodapeData = fs.readFileSync(path.join(ASSETS_DIR, "RODAPE_FISIOMED.png"));

  const genero = inferGenero(nome_paciente);
  let atendido;
  if (genero === "f") {
    atendido = "atendida";
  } else if (genero === "m") {
    atendido = "atendido";
  } else {
    atendido = "atendido(a)";
  }

  const diasExtenso = EXTENSO[dias] || String(dias);
  const diaPalavra = dias === 1 ? "dia" : "dias";

  const textoAtestado = `Atesto para os devidos fins que o(a) Sr(a). ${nome_paciente}, foi ${atendido} por mim nesta data, necessitando de afastamento de suas atividades por ${dias} (${diasExtenso}) ${diaPalavra}, a partir de ${data}.`;
  const textoCid = `CID-10: ${cid} – ${diagnostico}`;

  // Header
  const headerChildren = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 60 },
      children: [
        new ImageRun({ data: logoData, transformation: { width: 431, height: 187 }, type: "jpg" }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({ text: "Dr. Eduardo Soares de Carvalho", bold: true, size: 22, color: GREEN, font: "Calibri" }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({ text: "Ortopedia e Traumatologia", size: 20, color: GREEN, font: "Calibri" }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 80 },
      children: [
        new TextRun({ text: "CRM-PE 31277", size: 20, color: GREEN, font: "Calibri" }),
      ],
    }),
    new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: GREEN } },
      spacing: { after: 0 },
    }),
  ];

  // Footer
  const footerChildren = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new ImageRun({ data: rodapeData, transformation: { width: 493, height: 72 }, type: "jpg" }),
      ],
    }),
  ];

  // Body
  const bodyChildren = [];

  // Título
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 400, after: 400 },
      children: [
        new TextRun({ text: "ATESTADO MÉDICO", bold: true, size: 32, font: "Calibri" }),
      ],
    })
  );

  // Texto principal
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.JUSTIFIED,
      spacing: { after: 200, line: 360 },
      children: [
        new TextRun({ text: textoAtestado, size: 24, font: "Calibri" }),
      ],
    })
  );

  // CID
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.JUSTIFIED,
      spacing: { after: 200 },
      children: [
        new TextRun({ text: textoCid, size: 24, font: "Calibri" }),
      ],
    })
  );

  // Espaço + Assinatura
  bodyChildren.push(new Paragraph({ spacing: { before: 600 } }));

  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 40 },
      children: [
        new TextRun({ text: "_______________________________", size: 22, font: "Calibri" }),
      ],
    })
  );
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({ text: "Dr. Eduardo Soares de Carvalho", bold: true, size: 20, color: GREEN, font: "Calibri" }),
      ],
    })
  );
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({ text: "Ortopedia e Traumatologia", size: 20, color: GREEN, font: "Calibri" }),
      ],
    })
  );
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({ text: "CRM-PE 31277", size: 20, color: GREEN, font: "Calibri" }),
      ],
    })
  );

  // Local e data (abaixo do nome/CRM)
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 200 },
      children: [
        new TextRun({ text: `Palmares-PE, ${data}`, size: 22, font: "Calibri" }),
      ],
    })
  );

  const doc = new Document({
    sections: [
      {
        properties: {
          page: {
            margin: { top: 600, right: 800, bottom: 900, left: 800 },
          },
        },
        headers: { default: new Header({ children: headerChildren }) },
        footers: { default: new Footer({ children: footerChildren }) },
        children: bodyChildren,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);
  return outputPath;
}

// CLI
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Uso: node atestado.js <json_path> <output_path>");
    process.exit(1);
  }
  const jsonData = JSON.parse(fs.readFileSync(args[0], "utf-8"));
  gerarAtestado(jsonData, args[1])
    .then(() => console.log("OK:" + args[1]))
    .catch((err) => { console.error("ERRO:", err.message); process.exit(1); });
}

module.exports = { gerarAtestado };
