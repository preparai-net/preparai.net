/**
 * Gerador de Laudo Médico — Node.js com docx-js
 * DEVE caber em 1 página. Logo no Header, rodapé no Footer.
 *
 * Uso: node laudo.js <json_path> <output_path>
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
  Table,
  TableRow,
  TableCell,
  WidthType,
} = require("docx");

const ASSETS_DIR = path.join(__dirname, "..", "assets");
const GREEN = "2E5D34";

async function gerarLaudo(dados, outputPath) {
  const { nome_paciente, data, texto_laudo, config = {} } = dados;

  // Configurações dinâmicas do carimbo
  const cfgMedico = config.medico || "Dr. Eduardo Soares de Carvalho";
  const cfgEspecialidade = config.especialidade || "Ortopedia e Traumatologia";
  const cfgCrm = config.crm || "CRM-PE 31277";

  const logoData = fs.readFileSync(path.join(ASSETS_DIR, "LOGO_FISIOMED.png"));
  const rodapeData = fs.readFileSync(path.join(ASSETS_DIR, "RODAPE_FISIOMED.png"));

  // Determinar tamanho da fonte baseado no comprimento do texto
  let fontSize = 22; // 11pt
  if (texto_laudo.length > 1800) {
    fontSize = 20; // 10pt
  }
  if (texto_laudo.length > 2500) {
    fontSize = 18; // 9pt
  }

  // Header
  const headerChildren = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 60 },
      children: [
        new ImageRun({
          data: logoData,
          transformation: { width: 431, height: 187 },
          type: "jpg",
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({ text: cfgMedico, bold: true, size: 22, color: GREEN, font: "Calibri" }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({ text: cfgEspecialidade, size: 20, color: GREEN, font: "Calibri" }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 80 },
      children: [
        new TextRun({ text: cfgCrm, size: 20, color: GREEN, font: "Calibri" }),
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
        new ImageRun({
          data: rodapeData,
          transformation: { width: 493, height: 72 },
          type: "jpg",
        }),
      ],
    }),
  ];

  // Body
  const bodyChildren = [];

  // Título
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 200, after: 200 },
      children: [
        new TextRun({ text: "LAUDO MÉDICO", bold: true, size: 32, font: "Calibri" }),
      ],
    })
  );

  // Paciente + Data
  bodyChildren.push(
    new Table({
      width: { size: 100, type: WidthType.PERCENTAGE },
      borders: {
        top: { style: BorderStyle.NONE },
        bottom: { style: BorderStyle.NONE },
        left: { style: BorderStyle.NONE },
        right: { style: BorderStyle.NONE },
        insideHorizontal: { style: BorderStyle.NONE },
        insideVertical: { style: BorderStyle.NONE },
      },
      rows: [
        new TableRow({
          children: [
            new TableCell({
              width: { size: 70, type: WidthType.PERCENTAGE },
              borders: {
                top: { style: BorderStyle.NONE },
                bottom: { style: BorderStyle.NONE },
                left: { style: BorderStyle.NONE },
                right: { style: BorderStyle.NONE },
              },
              children: [
                new Paragraph({
                  children: [
                    new TextRun({ text: "Paciente: ", bold: true, size: fontSize, font: "Calibri" }),
                    new TextRun({ text: nome_paciente, size: fontSize, font: "Calibri" }),
                  ],
                }),
              ],
            }),
            new TableCell({
              width: { size: 30, type: WidthType.PERCENTAGE },
              borders: {
                top: { style: BorderStyle.NONE },
                bottom: { style: BorderStyle.NONE },
                left: { style: BorderStyle.NONE },
                right: { style: BorderStyle.NONE },
              },
              children: [
                new Paragraph({
                  alignment: AlignmentType.RIGHT,
                  children: [
                    new TextRun({ text: "Data: ", bold: true, size: fontSize, font: "Calibri" }),
                    new TextRun({ text: data, size: fontSize, font: "Calibri" }),
                  ],
                }),
              ],
            }),
          ],
        }),
      ],
    })
  );

  // Linha separadora
  bodyChildren.push(
    new Paragraph({
      border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" } },
      spacing: { after: 200 },
    })
  );

  // Texto do laudo — justificado, sem negrito nem caixa alta
  // Dividir por parágrafos (linhas duplas)
  const paragrafos = texto_laudo.split(/\n\n+/).filter(p => p.trim());
  paragrafos.forEach((p) => {
    // Dividir por quebras de linha simples
    const linhas = p.split(/\n/).filter(l => l.trim());
    const runs = [];
    linhas.forEach((linha, idx) => {
      if (idx > 0) runs.push(new TextRun({ text: " ", size: fontSize, font: "Calibri" }));
      runs.push(new TextRun({ text: linha.trim(), size: fontSize, font: "Calibri" }));
    });

    bodyChildren.push(
      new Paragraph({
        alignment: AlignmentType.JUSTIFIED,
        spacing: { after: 120 },
        children: runs,
      })
    );
  });

  // Espaço + Assinatura
  bodyChildren.push(new Paragraph({ spacing: { before: 300 } }));

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
        new TextRun({ text: cfgMedico, bold: true, size: 20, color: GREEN, font: "Calibri" }),
      ],
    })
  );
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({ text: cfgEspecialidade, size: 20, color: GREEN, font: "Calibri" }),
      ],
    })
  );
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({ text: cfgCrm, size: 20, color: GREEN, font: "Calibri" }),
      ],
    })
  );

  // Local e data (abaixo do nome/CRM)
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 200 },
      children: [
        new TextRun({ text: `Palmares-PE, ${data}`, size: 20, font: "Calibri" }),
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
    console.error("Uso: node laudo.js <json_path> <output_path>");
    process.exit(1);
  }
  const jsonData = JSON.parse(fs.readFileSync(args[0], "utf-8"));
  gerarLaudo(jsonData, args[1])
    .then(() => console.log("OK:" + args[1]))
    .catch((err) => { console.error("ERRO:", err.message); process.exit(1); });
}

module.exports = { gerarLaudo };
