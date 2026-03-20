// ================================================================
// FISIOMED — app.js — Lógica do Formulário
// ================================================================

// ========== BANCO DE CIDs ==========
const DIAGNOSTICOS = [
  { nome: "Lombalgia / Dor lombar baixa", cid: "M54.5" },
  { nome: "Lombociatalgia / Ciática cervical", cid: "M54.3" },
  { nome: "Lombociatalgia / Ciática lombar", cid: "M54.4" },
  { nome: "Espondilose lombar", cid: "M47.8" },
  { nome: "Espondilose cervical", cid: "M47.8" },
  { nome: "Discopatia degenerativa lombar c/ radiculopatia", cid: "M51.1" },
  { nome: "Discopatia cervical c/ radiculopatia", cid: "M50.1" },
  { nome: "Cervicalgia", cid: "M54.2" },
  { nome: "Dorsalgia", cid: "M54.9" },
  { nome: "Síndrome do manguito rotador", cid: "M75.1" },
  { nome: "Bursite subacromial", cid: "M75.5" },
  { nome: "Capsulite adesiva de ombro", cid: "M75.0" },
  { nome: "Tendinite bicipital", cid: "M75.2" },
  { nome: "Tendinite calcificante de ombro", cid: "M75.3" },
  { nome: "Gonartrose primária unilateral", cid: "M17.1" },
  { nome: "Gonartrose primária bilateral", cid: "M17.0" },
  { nome: "Gonartrose pós-traumática", cid: "M17.3" },
  { nome: "Coxartrose primária unilateral", cid: "M16.1" },
  { nome: "Coxartrose primária bilateral", cid: "M16.0" },
  { nome: "Artrose de tornozelo", cid: "M19.07" },
  { nome: "Artrose de cotovelo", cid: "M19.02" },
  { nome: "Artrose de punho", cid: "M19.03" },
  { nome: "Artrose de ombro", cid: "M19.01" },
  { nome: "Síndrome do túnel do carpo", cid: "G56.0" },
  { nome: "Tenossinovite de De Quervain", cid: "M65.4" },
  { nome: "Epicondilite lateral", cid: "M77.1" },
  { nome: "Epicondilite medial", cid: "M77.0" },
  { nome: "Tendinite dos extensores do punho", cid: "M65.8" },
  { nome: "Tendinite dos extensores do pé", cid: "M76.5" },
  { nome: "Tendinite patelar", cid: "M76.5" },
  { nome: "Tendinite do calcâneo (Aquiles)", cid: "M76.6" },
  { nome: "Esporão calcâneo / Fasciíte plantar", cid: "M77.3" },
  { nome: "Dedo em gatilho", cid: "M65.3" },
  { nome: "Dedo em martelo", cid: "M20.4" },
  { nome: "Hallux valgus", cid: "M20.1" },
  { nome: "Hallux rigidus", cid: "M20.2" },
  { nome: "Pé plano valgo", cid: "M21.4" },
  { nome: "Pé cavo", cid: "M21.6" },
  { nome: "Pé torto congênito", cid: "Q66.0" },
  { nome: "Osgood-Schlatter", cid: "M92.5" },
  { nome: "Osteoporose sem fratura patológica", cid: "M81.0" },
  { nome: "Osteoporose com fratura patológica", cid: "M80.0" },
  { nome: "Fratura de rádio distal", cid: "S52.5" },
  { nome: "Fratura de escafoide", cid: "S62.0" },
  { nome: "Fratura de metacarpo", cid: "S62.3" },
  { nome: "Fratura de falange da mão", cid: "S62.6" },
  { nome: "Fratura de clavícula", cid: "S42.0" },
  { nome: "Fratura de úmero proximal", cid: "S42.2" },
  { nome: "Fratura diafisária de úmero", cid: "S42.3" },
  { nome: "Fratura de olécrano", cid: "S52.0" },
  { nome: "Fratura de fêmur proximal", cid: "S72.0" },
  { nome: "Fratura diafisária de fêmur", cid: "S72.3" },
  { nome: "Fratura de rótula", cid: "S82.0" },
  { nome: "Fratura de platô tibial", cid: "S82.1" },
  { nome: "Fratura diafisária de tíbia", cid: "S82.2" },
  { nome: "Fratura de tornozelo bimaleolar", cid: "S82.8" },
  { nome: "Fratura de calcâneo", cid: "S92.0" },
  { nome: "Fratura de metatarso", cid: "S92.3" },
  { nome: "Fratura de falange do pé", cid: "S92.5" },
  { nome: "Fratura de vértebra cervical", cid: "S12.9" },
  { nome: "Fratura de vértebra torácica", cid: "S22.0" },
  { nome: "Fratura de vértebra lombar", cid: "S32.0" },
  { nome: "Luxação de ombro", cid: "S43.0" },
  { nome: "Luxação de cotovelo", cid: "S53.1" },
  { nome: "Luxação de quadril", cid: "S73.0" },
  { nome: "Luxação de joelho", cid: "S83.1" },
  { nome: "Luxação de tornozelo", cid: "S93.0" },
  { nome: "Entorse de joelho", cid: "S83.5" },
  { nome: "Entorse de tornozelo", cid: "S93.4" },
  { nome: "Entorse de punho", cid: "S63.5" },
  { nome: "Entorse cervical (whiplash)", cid: "S13.4" },
  { nome: "Lesão de menisco", cid: "M23.2" },
  { nome: "Lesão do ligamento cruzado anterior", cid: "S83.5" },
  { nome: "Contusão de joelho", cid: "S80.0" },
  { nome: "Contusão de ombro", cid: "S40.0" },
  { nome: "Contusão de tornozelo", cid: "S90.0" },
  { nome: "Contusão de cotovelo", cid: "S50.0" },
  { nome: "Contusão de quadril", cid: "S70.0" },
  { nome: "Sequela de fratura membro superior", cid: "T92.1" },
  { nome: "Sequela de fratura membro inferior", cid: "T93.1" },
  { nome: "Sequela de fratura de coluna", cid: "T91.1" },
  { nome: "Síndrome do impacto subacromial", cid: "M75.1" },
  { nome: "Síndrome do túnel do tarso", cid: "G57.5" },
  { nome: "Síndrome do túnel cubital", cid: "G56.2" },
  { nome: "Artrite séptica", cid: "M00.8" },
  { nome: "Artrite reumatoide", cid: "M06.9" },
  { nome: "Artropatia por gota", cid: "M10.0" },
  { nome: "Necrose avascular da cabeça do fêmur", cid: "M87.0" },
  { nome: "Escoliose idiopática", cid: "M41.1" },
  { nome: "Espondilite anquilosante", cid: "M45" },
  { nome: "Síndrome da banda iliotibial", cid: "M76.3" },
  { nome: "Bursite trocantérica", cid: "M70.6" },
  { nome: "Bursite de joelho pré-patelar", cid: "M70.4" },
  { nome: "Bursite de olécrano", cid: "M70.2" },
  { nome: "Fibromialgia", cid: "M79.7" },
  { nome: "Mialgia / Dor muscular", cid: "M79.1" },
  { nome: "Fraqueza muscular", cid: "M62.8" },
  { nome: "Enxaqueca sem aura", cid: "G43.0" },
  { nome: "Enxaqueca com aura", cid: "G43.1" },
  { nome: "Cefaleia tensional", cid: "G44.2" },
  { nome: "Epilepsia", cid: "G40.9" },
  { nome: "AVC isquêmico", cid: "I63.9" },
  { nome: "AVC hemorrágico", cid: "I61.9" },
  { nome: "Ataque isquêmico transitório", cid: "G45.9" },
  { nome: "Doença de Parkinson", cid: "G20" },
  { nome: "Demência não especificada", cid: "F03" },
  { nome: "Doença de Alzheimer", cid: "G30.9" },
  { nome: "Esclerose múltipla", cid: "G35" },
  { nome: "Neuropatia periférica", cid: "G62.9" },
  { nome: "Neuropatia diabética", cid: "E11.4" },
  { nome: "Neuralgia do trigêmeo", cid: "G50.0" },
  { nome: "Paralisia facial periférica", cid: "G51.0" },
  { nome: "Vertigem periférica (VPPB)", cid: "H81.1" },
  { nome: "Doença de Ménière", cid: "H81.0" },
  { nome: "Síndrome das pernas inquietas", cid: "G25.8" },
  { nome: "Tremor essencial", cid: "G25.0" },
  { nome: "Insônia", cid: "G47.0" },
  { nome: "Apneia do sono", cid: "G47.3" },
  { nome: "Hipertensão arterial essencial", cid: "I10" },
  { nome: "Hipertensão arterial secundária", cid: "I15.9" },
  { nome: "Insuficiência cardíaca congestiva", cid: "I50.0" },
  { nome: "Angina pectoris instável", cid: "I20.0" },
  { nome: "Angina pectoris estável", cid: "I20.8" },
  { nome: "Infarto agudo do miocárdio", cid: "I21.9" },
  { nome: "Arritmia cardíaca", cid: "I49.9" },
  { nome: "Fibrilação atrial", cid: "I48" },
  { nome: "Taquicardia supraventricular", cid: "I47.1" },
  { nome: "Doença arterial coronariana", cid: "I25.1" },
  { nome: "Cardiomiopatia dilatada", cid: "I42.0" },
  { nome: "Valvulopatia aórtica", cid: "I35.9" },
  { nome: "Valvulopatia mitral", cid: "I34.9" },
  { nome: "Prolapso de válvula mitral", cid: "I34.1" },
  { nome: "Varizes dos membros inferiores", cid: "I83.9" },
  { nome: "Trombose venosa profunda", cid: "I80.2" },
  { nome: "Tromboembolismo pulmonar", cid: "I26.9" },
  { nome: "Insuficiência venosa crônica", cid: "I87.2" },
  { nome: "Doença arterial periférica", cid: "I73.9" },
  { nome: "Síndrome de Raynaud", cid: "I73.0" },
  { nome: "Diabetes mellitus tipo 1", cid: "E10.9" },
  { nome: "Diabetes mellitus tipo 2", cid: "E11.9" },
  { nome: "Hipotireoidismo primário", cid: "E03.9" },
  { nome: "Hipertireoidismo", cid: "E05.9" },
  { nome: "Tireoidite de Hashimoto", cid: "E06.3" },
  { nome: "Nódulo de tireoide", cid: "E04.1" },
  { nome: "Obesidade não especificada", cid: "E66.9" },
  { nome: "Obesidade mórbida", cid: "E66.0" },
  { nome: "Síndrome metabólica", cid: "E88.8" },
  { nome: "Dislipidemia", cid: "E78.5" },
  { nome: "Hipercolesterolemia", cid: "E78.0" },
  { nome: "Hipertrigliceridemia", cid: "E78.1" },
  { nome: "Deficiência de vitamina D", cid: "E55.9" },
  { nome: "Anemia ferropriva", cid: "D50.9" },
  { nome: "Artrite reumatoide soropositiva", cid: "M05.9" },
  { nome: "Artrite reumatoide soronegativa", cid: "M06.0" },
  { nome: "Lúpus eritematoso sistêmico", cid: "M32.9" },
  { nome: "Esclerodermia", cid: "M34.9" },
  { nome: "Síndrome de Sjögren", cid: "M35.0" },
  { nome: "Polimialgia reumática", cid: "M35.3" },
  { nome: "Artrite psoriásica", cid: "M07.3" },
  { nome: "Condrocalcinose", cid: "M11.2" },
  { nome: "Gastrite crônica", cid: "K29.5" },
  { nome: "Úlcera gástrica", cid: "K25.9" },
  { nome: "Doença do refluxo gastroesofágico", cid: "K21.0" },
  { nome: "Hérnia hiatal", cid: "K44.9" },
  { nome: "Síndrome do intestino irritável", cid: "K58.9" },
  { nome: "Doença de Crohn", cid: "K50.9" },
  { nome: "Retocolite ulcerativa", cid: "K51.9" },
  { nome: "Constipação intestinal", cid: "K59.0" },
  { nome: "Hemorroidas", cid: "K64.9" },
  { nome: "Hepatite B crônica", cid: "B18.1" },
  { nome: "Hepatite C crônica", cid: "B18.2" },
  { nome: "Cirrose hepática", cid: "K74.6" },
  { nome: "Esteatose hepática", cid: "K76.0" },
  { nome: "Colelitíase", cid: "K80.2" },
  { nome: "Pancreatite crônica", cid: "K86.1" },
  { nome: "Asma brônquica", cid: "J45.9" },
  { nome: "DPOC", cid: "J44.1" },
  { nome: "Bronquite crônica", cid: "J42" },
  { nome: "Pneumonia bacteriana", cid: "J18.9" },
  { nome: "Rinite alérgica", cid: "J30.4" },
  { nome: "Sinusite crônica", cid: "J32.9" },
  { nome: "Derrame pleural", cid: "J90" },
  { nome: "Fibrose pulmonar", cid: "J84.1" },
  { nome: "Tuberculose pulmonar", cid: "A15.3" },
  { nome: "Tosse crônica", cid: "R05" },
  { nome: "Infecção do trato urinário", cid: "N39.0" },
  { nome: "Cistite", cid: "N30.9" },
  { nome: "Nefrolitíase", cid: "N20.0" },
  { nome: "Insuficiência renal crônica", cid: "N18.9" },
  { nome: "Hiperplasia benigna da próstata", cid: "N40" },
  { nome: "Prostatite", cid: "N41.9" },
  { nome: "Incontinência urinária", cid: "N39.4" },
  { nome: "Bexiga hiperativa", cid: "N32.8" },
  { nome: "Disfunção erétil", cid: "N48.4" },
  { nome: "Varicocele", cid: "I86.1" },
  { nome: "Supervisão de gravidez normal", cid: "Z34" },
  { nome: "Gravidez de alto risco", cid: "O09.9" },
  { nome: "Endometriose", cid: "N80.9" },
  { nome: "Mioma uterino", cid: "D25.9" },
  { nome: "Ovário policístico", cid: "E28.2" },
  { nome: "Dismenorreia", cid: "N94.4" },
  { nome: "Menopausa", cid: "N95.1" },
  { nome: "Doença inflamatória pélvica", cid: "N73.9" },
  { nome: "Infertilidade feminina", cid: "N97.9" },
  { nome: "Dermatite atópica", cid: "L20.9" },
  { nome: "Dermatite de contato", cid: "L25.9" },
  { nome: "Psoríase", cid: "L40.9" },
  { nome: "Acne vulgar", cid: "L70.0" },
  { nome: "Urticária", cid: "L50.9" },
  { nome: "Herpes zoster", cid: "B02.9" },
  { nome: "Celulite infecciosa", cid: "L03.9" },
  { nome: "Erisipela", cid: "A46" },
  { nome: "Vitiligo", cid: "L80" },
  { nome: "Carcinoma basocelular", cid: "C44.9" },
  { nome: "Miopia", cid: "H52.1" },
  { nome: "Hipermetropia", cid: "H52.0" },
  { nome: "Astigmatismo", cid: "H52.2" },
  { nome: "Catarata", cid: "H26.9" },
  { nome: "Glaucoma", cid: "H40.9" },
  { nome: "Retinopatia diabética", cid: "H36.0" },
  { nome: "Conjuntivite alérgica", cid: "H10.1" },
  { nome: "Olho seco", cid: "H04.1" },
  { nome: "Amigdalite crônica", cid: "J35.0" },
  { nome: "Otite média aguda", cid: "H66.0" },
  { nome: "Otite média crônica", cid: "H66.3" },
  { nome: "Surdez neurossensorial", cid: "H90.4" },
  { nome: "Zumbido (tinnitus)", cid: "H93.1" },
  { nome: "Pólipos nasais", cid: "J33.9" },
  { nome: "Desvio de septo nasal", cid: "J34.2" },
  { nome: "Ronco", cid: "R06.5" },
  { nome: "Episódio depressivo leve", cid: "F32.0" },
  { nome: "Episódio depressivo moderado", cid: "F32.1" },
  { nome: "Episódio depressivo grave", cid: "F32.2" },
  { nome: "Transtorno depressivo recorrente", cid: "F33.9" },
  { nome: "Transtorno de ansiedade generalizada", cid: "F41.1" },
  { nome: "Ansiedade não especificada", cid: "F41.9" },
  { nome: "Transtorno do pânico", cid: "F41.0" },
  { nome: "TOC", cid: "F42.9" },
  { nome: "TEPT", cid: "F43.1" },
  { nome: "Transtorno bipolar", cid: "F31.9" },
  { nome: "Dependência de álcool", cid: "F10.2" },
  { nome: "TDAH", cid: "F90.0" },
  { nome: "Autismo", cid: "F84.0" },
  { nome: "Anorexia nervosa", cid: "F50.0" },
  { nome: "Síndrome de burnout", cid: "Z73.0" },
  { nome: "Hérnia inguinal", cid: "K40.9" },
  { nome: "Hérnia umbilical", cid: "K42.9" },
  { nome: "Hérnia incisional", cid: "K43.9" },
  { nome: "Apendicite aguda", cid: "K37" },
  { nome: "Fissura anal", cid: "K60.2" },
  { nome: "Lipoma", cid: "D17.9" },
  { nome: "Cisto sebáceo", cid: "L72.1" },
  { nome: "Supervisão de saúde da criança", cid: "Z00.1" },
  { nome: "Atraso no desenvolvimento", cid: "F88" },
  { nome: "Febre sem causa identificada", cid: "R50.9" },
  { nome: "Doença de Legg-Calvé-Perthes", cid: "M91.1" },
  { nome: "Genu valgum", cid: "M21.0" },
  { nome: "Genu varum", cid: "M21.1" },
  { nome: "Obesidade infantil", cid: "E66.9" },
  { nome: "HIV/AIDS", cid: "B24" },
  { nome: "Sífilis", cid: "A53.9" },
  { nome: "Dengue", cid: "A97.9" },
  { nome: "Leptospirose", cid: "A27.9" },
  { nome: "Neoplasia maligna de mama", cid: "C50.9" },
  { nome: "Neoplasia maligna de próstata", cid: "C61" },
  { nome: "Neoplasia maligna de cólon", cid: "C18.9" },
  { nome: "Neoplasia maligna de pulmão", cid: "C34.9" },
  { nome: "Neoplasia maligna de ossos", cid: "C41.9" },
  { nome: "Neoplasia maligna de tecidos moles", cid: "C49.9" },
  { nome: "Leucemia", cid: "C95.9" },
  { nome: "Linfoma não-Hodgkin", cid: "C85.9" },
  { nome: "Neoplasia benigna de osso", cid: "D16.9" },
  { nome: "Investigação de neoplasia", cid: "Z03.1" },
  { nome: "Sarcopenia", cid: "M62.8" },
  { nome: "Síndrome de fragilidade do idoso", cid: "R54" },
  { nome: "Queda recorrente no idoso", cid: "R29.6" },
  { nome: "Demência vascular", cid: "F01.9" },
  { nome: "Desnutrição", cid: "E46" },
  { nome: "Anemia não especificada", cid: "D64.9" },
  { nome: "Dor crônica", cid: "R52.1" },
  { nome: "Dor aguda", cid: "R52.0" },
  { nome: "Avaliação pré-operatória", cid: "Z01.8" },
  { nome: "Exame médico de rotina", cid: "Z00.0" },
  { nome: "Atestado de saúde ocupacional", cid: "Z02.1" },
  { nome: "Solicitação de benefício INSS", cid: "Z02.7" }
];

// ========== MEDICAMENTOS — RECEITA SIMPLES ==========
const MEDS_SIMPLES = [
  { nome: "DUOFLAM", posologia: "APLICAR 01 FRASCO-AMPOLA VIA INTRAMUSCULAR NO GLÚTEO – DOSE ÚNICA", qtd: "01 CX", tipo: "im" },
  { nome: "MELOXICAM 15MG", posologia: "TOMAR 01 COMPRIMIDO VIA ORAL DE 24/24H POR 05 DIAS", qtd: "01 CX", tipo: "oral" },
  { nome: "DIPIRONA 1G", posologia: "TOMAR 01 COMPRIMIDO VIA ORAL DE 6/6H POR 05 DIAS", qtd: "01 CX", tipo: "oral" },
  { nome: "MUSCULARE 10MG", posologia: "TOMAR 01 COMPRIMIDO VIA ORAL DE 12/12H POR 03 DIAS", qtd: "01 CX", tipo: "oral" },
  { nome: "NIVUX 100+20MG", posologia: "TOMAR 01 COMPRIMIDO VIA ORAL DE 12/12H POR 03 DIAS", qtd: "01 CX", tipo: "oral" },
  { nome: "PARACETAMOL 500MG", posologia: "TOMAR 01 COMPRIMIDO VIA ORAL DE 8/8H POR 03 DIAS", qtd: "01 CX", tipo: "oral" },
  { nome: "KETALGI 500MG", posologia: "TOMAR 01 COMPRIMIDO VIA ORAL DE 12/12H POR 05 DIAS", qtd: "01 CX", tipo: "oral" },
  { nome: "MIOSAN CAF 10MG", posologia: "TOMAR 01 COMPRIMIDO VIA ORAL DE 12/12H POR 03 DIAS", qtd: "01 CX", tipo: "oral" },
  { nome: "BEMOVE CURCUMA", posologia: "TOMAR 01 COMPRIMIDO VIA ORAL DE 24/24H", qtd: "01 CX", tipo: "oral" },
  { nome: "LISADOR DIP 1G", posologia: "TOMAR 01 COMPRIMIDO VIA ORAL DE 6/6H POR 05 DIAS", qtd: "01 CX", tipo: "oral" }
];

// ========== MEDICAMENTOS — RECEITA ESPECIAL ==========
const MEDS_ESPECIAIS = [
  { nome: "COQUES 200MG", posologia: "Tomar 01 comprimido via oral de 12/12h por 03 dias", qtd: "01 CX" },
  { nome: "GESICO RETARD 100MG", posologia: "Tomar 01 comprimido via oral de 12/12h por 05 dias", qtd: "01 CX" },
  { nome: "MOBALE 75MG (12/12h)", posologia: "Tomar 01 comprimido via oral de 12/12h", qtd: "02 CX" },
  { nome: "MOBALE 75MG (24/24h)", posologia: "Tomar 01 comprimido via oral de 24/24h à noite", qtd: "01 CX" },
  { nome: "PREGABALINA 75MG (12/12h)", posologia: "Tomar 01 comprimido via oral de 12/12h", qtd: "02 CX" },
  { nome: "PREGABALINA 75MG (24/24h)", posologia: "Tomar 01 comprimido via oral de 24/24h à noite", qtd: "01 CX" },
  { nome: "TRAMADOL RETARD 100MG", posologia: "Tomar 01 comprimido via oral de 12/12h se apresentar dor forte", qtd: "01 CX" },
  { nome: "PACO 500+30MG", posologia: "Tomar 01 comprimido via oral de 8/8h se apresentar dor forte", qtd: "01 CX" },
  { nome: "GABAPENTINA 300MG", posologia: "Tomar 01 comprimido via oral de 8/8h", qtd: "02 CX" },
  { nome: "DULOXETINA 30MG", posologia: "Tomar 01 comprimido via oral de 24/24h", qtd: "02 CX" },
  { nome: "CEFALEXINA 500MG", posologia: "Tomar 01 comprimido via oral de 6/6h por 07 dias", qtd: "01 CX" },
  { nome: "AMOCLAV 875+125MG", posologia: "Tomar 01 comprimido via oral de 12/12h por 10 dias", qtd: "01 CX" }
];

// ========== INICIALIZAÇÃO ==========
document.addEventListener('DOMContentLoaded', () => {
  // Data padrão = hoje
  const hoje = new Date();
  const dataInput = document.getElementById('data');
  dataInput.value = hoje.toISOString().split('T')[0];

  // Autocomplete diagnóstico
  setupAutocomplete('diagnostico1', 'ac_diag1', 'cid1');

  // Preencher justificativa retorno
  updateJustificativas();

  // Quando região muda, atualizar justificativas
  document.getElementById('regiao').addEventListener('input', updateJustificativas);

  // Gerar listas de medicamentos
  renderMedicamentos('receita_simples_list', MEDS_SIMPLES, 'rs');
  renderMedicamentos('receita_especial_list', MEDS_ESPECIAIS, 're');

  // Adicionar "OUTRO MEDICAMENTO" nas receitas
  renderOutroMedicamento('receita_simples_list', 'rs');
  renderOutroMedicamento('receita_especial_list', 're');

  // Submit
  document.getElementById('mainForm').addEventListener('submit', handleSubmit);
});

// ========== AUTOCOMPLETE ==========
function setupAutocomplete(inputId, listId, cidId) {
  const input = document.getElementById(inputId);
  const list = document.getElementById(listId);
  const cidInput = document.getElementById(cidId);
  let activeIdx = -1;

  input.addEventListener('input', () => {
    const val = input.value.toLowerCase().trim();
    if (val.length < 2) { list.classList.remove('show'); return; }

    const filtered = DIAGNOSTICOS.filter(d =>
      d.nome.toLowerCase().includes(val) || d.cid.toLowerCase().includes(val)
    ).slice(0, 15);

    if (filtered.length === 0) { list.classList.remove('show'); return; }

    list.innerHTML = filtered.map((d, i) =>
      `<div class="autocomplete-item" data-idx="${i}">${d.nome} <span class="cid">${d.cid}</span></div>`
    ).join('');
    list.classList.add('show');
    activeIdx = -1;

    list.querySelectorAll('.autocomplete-item').forEach(item => {
      item.addEventListener('click', () => {
        const idx = parseInt(item.dataset.idx);
        input.value = filtered[idx].nome;
        cidInput.value = filtered[idx].cid;
        list.classList.remove('show');
      });
    });
  });

  input.addEventListener('keydown', (e) => {
    const items = list.querySelectorAll('.autocomplete-item');
    if (!items.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIdx = Math.min(activeIdx + 1, items.length - 1);
      items.forEach((it, i) => it.classList.toggle('active', i === activeIdx));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIdx = Math.max(activeIdx - 1, 0);
      items.forEach((it, i) => it.classList.toggle('active', i === activeIdx));
    } else if (e.key === 'Enter' && activeIdx >= 0) {
      e.preventDefault();
      items[activeIdx].click();
    }
  });

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !list.contains(e.target)) {
      list.classList.remove('show');
    }
  });
}

// ========== TOGGLE CHECKBOXES COM EXPAND ==========
function toggleCheck(id) {
  const cb = document.getElementById(id);
  cb.checked = !cb.checked;
  const expand = document.getElementById(id + '_expand');
  if (expand) {
    expand.classList.toggle('open', cb.checked);
  }
}

// ========== JUSTIFICATIVAS PRÉ-PREENCHIDAS ==========
function updateJustificativas() {
  const regiao = document.getElementById('regiao').value || '[REGIÃO]';
  const base = `Paciente em acompanhamento com ortopedista, com quadro de dor e limitação funcional em ${regiao} em seguimento diagnóstico-terapêutico.`;

  document.getElementById('apac_retorno_just').value = base;

  // Fisioterapia
  const fisioRegiao = document.getElementById('apac_fisio_regiao');
  if (!fisioRegiao.value || fisioRegiao.dataset.auto !== 'false') {
    fisioRegiao.value = regiao;
    fisioRegiao.dataset.auto = 'true';
  }
  const fisioJust = document.getElementById('apac_fisio_just');
  if (!fisioJust.value || fisioJust.dataset.auto !== 'false') {
    fisioJust.value = base;
    fisioJust.dataset.auto = 'true';
  }

  // RMN
  const rmnRegiao = document.getElementById('apac_rmn_regiao');
  if (!rmnRegiao.value || rmnRegiao.dataset.auto !== 'false') {
    rmnRegiao.value = regiao;
    rmnRegiao.dataset.auto = 'true';
  }
  const rmnJust = document.getElementById('apac_rmn_just');
  if (!rmnJust.value || rmnJust.dataset.auto !== 'false') {
    rmnJust.value = base + ' Necessitando de investigação complementar.';
    rmnJust.dataset.auto = 'true';
  }

  // RX
  const rxRegiao = document.getElementById('apac_rx_regiao');
  if (!rxRegiao.value || rxRegiao.dataset.auto !== 'false') {
    rxRegiao.value = regiao;
    rxRegiao.dataset.auto = 'true';
  }
  const rxJust = document.getElementById('apac_rx_just');
  if (!rxJust.value || rxJust.dataset.auto !== 'false') {
    rxJust.value = base + ' Solicitada radiografia para investigação complementar.';
    rxJust.dataset.auto = 'true';
  }

  // USG
  const usgRegiao = document.getElementById('apac_usg_regiao');
  if (!usgRegiao.value || usgRegiao.dataset.auto !== 'false') {
    usgRegiao.value = regiao;
    usgRegiao.dataset.auto = 'true';
  }
  const usgJust = document.getElementById('apac_usg_just');
  if (!usgJust.value || usgJust.dataset.auto !== 'false') {
    usgJust.value = base + ' Necessitando de investigação complementar.';
    usgJust.dataset.auto = 'true';
  }

  // TC
  const tcRegiao = document.getElementById('apac_tc_regiao');
  if (!tcRegiao.value || tcRegiao.dataset.auto !== 'false') {
    tcRegiao.value = regiao;
    tcRegiao.dataset.auto = 'true';
  }
  const tcJust = document.getElementById('apac_tc_just');
  if (!tcJust.value || tcJust.dataset.auto !== 'false') {
    tcJust.value = base + ' Necessitando de investigação complementar.';
    tcJust.dataset.auto = 'true';
  }
}

// Marcar campo como editado manualmente
['apac_fisio_regiao','apac_fisio_just','apac_rmn_regiao','apac_rmn_just',
 'apac_rx_regiao','apac_rx_just','apac_usg_regiao','apac_usg_just',
 'apac_tc_regiao','apac_tc_just'].forEach(id => {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener('input', () => { el.dataset.auto = 'false'; });
  }
});

// ========== RENDERIZAR MEDICAMENTOS ==========
function renderMedicamentos(containerId, meds, prefix) {
  const container = document.getElementById(containerId);
  meds.forEach((med, i) => {
    const id = `${prefix}_${i}`;
    const div = document.createElement('div');
    div.className = 'med-item';
    div.innerHTML = `
      <input type="checkbox" id="${id}" onclick="toggleMedExpand('${id}')">
      <div class="med-info">
        <div class="med-name">${med.nome}</div>
        <div class="med-expand" id="${id}_expand">
          <div class="field">
            <label>Posologia</label>
            <textarea id="${id}_pos" rows="2">${med.posologia}</textarea>
          </div>
          <div class="field">
            <label>Quantidade</label>
            <input type="text" id="${id}_qtd" value="${med.qtd}">
          </div>
        </div>
      </div>
    `;
    container.appendChild(div);
  });
}

function renderOutroMedicamento(containerId, prefix) {
  const container = document.getElementById(containerId);
  const id = `${prefix}_outro`;
  const div = document.createElement('div');
  div.className = 'med-item';
  div.innerHTML = `
    <input type="checkbox" id="${id}" onclick="toggleMedExpand('${id}')">
    <div class="med-info">
      <div class="med-name">OUTRO MEDICAMENTO</div>
      <div class="med-expand" id="${id}_expand">
        <div class="field">
          <label>Nome do medicamento</label>
          <input type="text" id="${id}_nome" placeholder="Nome completo">
        </div>
        <div class="field">
          <label>Posologia</label>
          <textarea id="${id}_pos" rows="2" placeholder="Posologia completa"></textarea>
        </div>
        <div class="field">
          <label>Quantidade</label>
          <input type="text" id="${id}_qtd" value="01 CX">
        </div>
      </div>
    </div>
  `;
  container.appendChild(div);
}

function toggleMedExpand(id) {
  const cb = document.getElementById(id);
  const expand = document.getElementById(id + '_expand');
  if (expand) {
    expand.classList.toggle('open', cb.checked);
  }
}

// ========== COLETAR DADOS E ENVIAR ==========
function formatDateBR(dateStr) {
  // dateStr = "YYYY-MM-DD"
  const parts = dateStr.split('-');
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function collectData() {
  const nome = document.getElementById('nome_paciente').value.trim().toUpperCase();
  const dataVal = document.getElementById('data').value;
  const data = formatDateBR(dataVal);

  // Diagnóstico
  const diagnostico1 = document.getElementById('diagnostico1').value.trim();
  const cid1 = document.getElementById('cid1').value.trim();
  const regiao = document.getElementById('regiao').value.trim().toUpperCase();
  const observacao_clinica = document.getElementById('observacao_clinica').value.trim();

  // APACs
  const apacs = {
    retorno: {
      ativo: true,
      justificativa: document.getElementById('apac_retorno_just').value.trim()
    },
    fisioterapia: {
      ativo: document.getElementById('apac_fisio').checked,
      regiao: document.getElementById('apac_fisio_regiao').value.trim().toUpperCase(),
      justificativa: document.getElementById('apac_fisio_just').value.trim()
    },
    rmn: {
      ativo: document.getElementById('apac_rmn').checked,
      regiao: document.getElementById('apac_rmn_regiao').value.trim().toUpperCase(),
      justificativa: document.getElementById('apac_rmn_just').value.trim()
    },
    radiografia: {
      ativo: document.getElementById('apac_rx').checked,
      regiao: document.getElementById('apac_rx_regiao').value.trim().toUpperCase(),
      incidencia: document.getElementById('apac_rx_incidencia').value,
      justificativa: document.getElementById('apac_rx_just').value.trim()
    },
    usg: {
      ativo: document.getElementById('apac_usg').checked,
      regiao: document.getElementById('apac_usg_regiao').value.trim().toUpperCase(),
      justificativa: document.getElementById('apac_usg_just').value.trim()
    },
    tc: {
      ativo: document.getElementById('apac_tc').checked,
      regiao: document.getElementById('apac_tc_regiao').value.trim().toUpperCase(),
      justificativa: document.getElementById('apac_tc_just').value.trim()
    },
    consulta: {
      ativo: document.getElementById('apac_consulta').checked,
      especialidade: (document.getElementById('apac_consulta_esp').value || '').trim().toUpperCase(),
      justificativa: (document.getElementById('apac_consulta_just').value || '').trim()
    },
    outra: {
      ativo: document.getElementById('apac_outra').checked,
      procedimento: (document.getElementById('apac_outra_proc').value || '').trim().toUpperCase(),
      justificativa: (document.getElementById('apac_outra_just').value || '').trim()
    }
  };

  // Receita Simples
  const receita_simples = [];
  MEDS_SIMPLES.forEach((med, i) => {
    const id = `rs_${i}`;
    if (document.getElementById(id).checked) {
      receita_simples.push({
        nome: med.nome,
        posologia: document.getElementById(`${id}_pos`).value.trim(),
        quantidade: document.getElementById(`${id}_qtd`).value.trim(),
        tipo: med.tipo
      });
    }
  });
  // Outro
  if (document.getElementById('rs_outro').checked) {
    const outroNome = document.getElementById('rs_outro_nome').value.trim().toUpperCase();
    if (outroNome) {
      receita_simples.push({
        nome: outroNome,
        posologia: document.getElementById('rs_outro_pos').value.trim(),
        quantidade: document.getElementById('rs_outro_qtd').value.trim(),
        tipo: 'oral'
      });
    }
  }

  // Receita Especial
  const receita_especial = [];
  MEDS_ESPECIAIS.forEach((med, i) => {
    const id = `re_${i}`;
    if (document.getElementById(id).checked) {
      receita_especial.push({
        nome: med.nome,
        posologia: document.getElementById(`${id}_pos`).value.trim(),
        quantidade: document.getElementById(`${id}_qtd`).value.trim()
      });
    }
  });
  // Outro medicamento especial
  if (document.getElementById('re_outro').checked) {
    const outroNome = document.getElementById('re_outro_nome').value.trim().toUpperCase();
    if (outroNome) {
      receita_especial.push({
        nome: outroNome,
        posologia: document.getElementById('re_outro_pos').value.trim(),
        quantidade: document.getElementById('re_outro_qtd').value.trim()
      });
    }
  }

  // Atestado
  const atestado = {
    ativo: document.getElementById('atestado_ativo').checked,
    dias: parseInt(document.getElementById('atestado_dias').value) || 1
  };

  // Laudo
  const laudo = {
    ativo: document.getElementById('laudo_ativo').checked,
    texto: document.getElementById('laudo_texto').value.trim()
  };

  return {
    nome_paciente: nome,
    data,
    diagnostico1,
    cid1,
    regiao,
    observacao_clinica,
    apacs,
    receita_simples,
    receita_especial,
    atestado,
    laudo
  };
}

async function handleSubmit(e) {
  e.preventDefault();

  const errorDiv = document.getElementById('errorMsg');
  errorDiv.classList.remove('show');

  // Validações
  const nome = document.getElementById('nome_paciente').value.trim();
  if (!nome) {
    showError('Por favor, preencha o nome do paciente.');
    return;
  }
  const diag = document.getElementById('diagnostico1').value.trim();
  if (!diag) {
    showError('Por favor, preencha o diagnóstico principal.');
    return;
  }
  const cid = document.getElementById('cid1').value.trim();
  if (!cid) {
    showError('Por favor, selecione um CID para o diagnóstico principal.');
    return;
  }

  const data = collectData();

  // Mostrar overlay
  document.getElementById('overlay').classList.add('show');
  document.getElementById('btnGerar').disabled = true;

  try {
    const resp = await fetch('/fisiomed/gerar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(errText || 'Erro ao gerar documentos');
    }

    // Download do PDF
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = data.nome_paciente.replace(/\s+/g, '_') + '.pdf';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

  } catch (err) {
    showError('Erro: ' + err.message);
  } finally {
    document.getElementById('overlay').classList.remove('show');
    document.getElementById('btnGerar').disabled = false;
  }
}

function showError(msg) {
  const errorDiv = document.getElementById('errorMsg');
  errorDiv.textContent = msg;
  errorDiv.classList.add('show');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
