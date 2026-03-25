/**
 * Gerador de Receita Simples — Node.js com docx-js
 * Gera .docx do zero com cabeçalho, medicamentos e rodapé.
 *
 * Uso: node receita_simples.js <json_path> <output_path>
 *   json_path: caminho para arquivo JSON com dados da receita
 *   output_path: caminho de saída do .docx
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
  TabStopType,
  TabStopPosition,
  PageOrientation,
} = require("docx");

const ASSETS_DIR = path.join(__dirname, "..", "assets");
const GREEN = "2E5D34";

async function gerarReceitaSimples(dados, outputPath) {
  const {
    nome_paciente,
    data,
    medicamentos, // array de { nome, posologia, quantidade }
    tipo_uso,     // "USO ORAL" ou "USO INTRAMUSCULAR"
    config = {},
  } = dados;

  // Configurações dinâmicas do carimbo
  const cfgMedico = config.medico || "Dr. Eduardo Soares de Carvalho";
  const cfgEspecialidade = config.especialidade || "Ortopedia e Traumatologia";
  const cfgCrm = config.crm || "CRM-PE 31277";

  // Ler imagens
  const logoData = fs.readFileSync(path.join(ASSETS_DIR, "LOGO_FISIOMED.png"));
  const rodapeData = fs.readFileSync(path.join(ASSETS_DIR, "RODAPE_FISIOMED.png"));

  // Header com logo + dados médico
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
        new TextRun({
          text: cfgMedico,
          bold: true,
          size: 22,
          color: GREEN,
          font: "Calibri",
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({
          text: cfgEspecialidade,
          size: 20,
          color: GREEN,
          font: "Calibri",
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 80 },
      children: [
        new TextRun({
          text: cfgCrm,
          size: 20,
          color: GREEN,
          font: "Calibri",
        }),
      ],
    }),
    // Linha separadora verde
    new Paragraph({
      border: {
        bottom: { style: BorderStyle.SINGLE, size: 6, color: GREEN },
      },
      spacing: { after: 0 },
    }),
  ];

  // Footer com rodapé
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
        new TextRun({
          text: "RECEITUÁRIO",
          bold: true,
          size: 28,
          font: "Calibri",
        }),
      ],
    })
  );

  // Paciente + Data na mesma linha (tabela sem bordas)
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
                    new TextRun({ text: "Paciente: ", bold: true, size: 22, font: "Calibri" }),
                    new TextRun({ text: nome_paciente, size: 22, font: "Calibri" }),
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
                    new TextRun({ text: "Data: ", bold: true, size: 22, font: "Calibri" }),
                    new TextRun({ text: data, size: 22, font: "Calibri" }),
                  ],
                }),
              ],
            }),
          ],
        }),
      ],
    })
  );

  // Linha separadora fina cinza
  bodyChildren.push(
    new Paragraph({
      border: {
        bottom: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
      },
      spacing: { after: 200 },
    })
  );

  // Tipo de uso
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 100, after: 200 },
      children: [
        new TextRun({
          text: tipo_uso,
          bold: true,
          size: 24,
          font: "Calibri",
        }),
      ],
    })
  );

  // Medicamentos
  medicamentos.forEach((med, idx) => {
    const num = idx + 1;
    const dashes = " " + "-".repeat(40 - med.nome.length > 5 ? 40 - med.nome.length : 5) + " ";

    // Linha do medicamento: "1. MELOXICAM 15MG ---- 01 CX"
    bodyChildren.push(
      new Paragraph({
        spacing: { before: 100, after: 40 },
        children: [
          new TextRun({
            text: `${num}. ${med.nome}${dashes}${med.quantidade}`,
            bold: true,
            size: 22,
            font: "Calibri",
          }),
        ],
      })
    );

    // Posologia (com indent)
    bodyChildren.push(
      new Paragraph({
        spacing: { after: 200 },
        indent: { left: 480 },
        children: [
          new TextRun({
            text: med.posologia,
            size: 22,
            font: "Calibri",
          }),
        ],
      })
    );
  });

  // Espaço antes da assinatura
  bodyChildren.push(
    new Paragraph({ spacing: { before: 400 } })
  );

  // Assinatura
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 40 },
      children: [
        new TextRun({
          text: "_______________________________",
          size: 22,
          font: "Calibri",
        }),
      ],
    })
  );
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({
          text: cfgMedico,
          bold: true,
          size: 20,
          font: "Calibri",
          color: GREEN,
        }),
      ],
    })
  );
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 0 },
      children: [
        new TextRun({
          text: cfgEspecialidade,
          size: 20,
          font: "Calibri",
          color: GREEN,
        }),
      ],
    })
  );
  bodyChildren.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({
          text: cfgCrm,
          size: 20,
          font: "Calibri",
          color: GREEN,
        }),
      ],
    })
  );

  const doc = new Document({
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: 600,
              right: 800,
              bottom: 900,
              left: 800,
            },
          },
        },
        headers: {
          default: new Header({ children: headerChildren }),
        },
        footers: {
          default: new Footer({ children: footerChildren }),
        },
        children: bodyChildren,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);
  return outputPath;
}

// ========== CLI ==========
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Uso: node receita_simples.js <json_path> <output_path>");
    process.exit(1);
  }

  const jsonData = JSON.parse(fs.readFileSync(args[0], "utf-8"));
  const outputPath = args[1];

  gerarReceitaSimples(jsonData, outputPath)
    .then(() => {
      console.log("OK:" + outputPath);
    })
    .catch((err) => {
      console.error("ERRO:", err.message);
      process.exit(1);
    });
}

module.exports = { gerarReceitaSimples };
