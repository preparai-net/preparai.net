"""
Taxonomia Híbrida PREPARAI — Classificação automática local de questões TEOT.

Três níveis: Categoria → Subtema → Sub-subtema
Subtemas-ponte: compartilhados entre categorias (sem duplicar questões).

Uso:
    from app.generators.taxonomy import suggest_classification
    result = suggest_classification(enunciado, alternativas, categoria_atual)
    # result = {'categoria': '...', 'subtema': '...', 'sub_subtema': '...', 'confidence': 0.85}
"""

import re
from typing import Optional

# ============================================================
# CATEGORIAS OFICIAIS (nomes fixos, não alterar)
# ============================================================
CATEGORIAS_OFICIAIS = [
    'Básicas',
    'Quadril',
    'Joelho',
    'Ombro e cotovelo',
    'Pé e tornozelo',
    'Mão e punho',
    'Coluna',
    'Pediatria',
    'Trauma',
    'Tumores',
]

# ============================================================
# NORMALIZAÇÃO DE CATEGORIAS
# Mapeia variações comuns → nome oficial
# ============================================================
_CATEGORY_ALIASES = {
    # Básicas
    'basicas': 'Básicas', 'basica': 'Básicas', 'básica': 'Básicas',
    'básicas': 'Básicas', 'ciencias basicas': 'Básicas',
    'ciências básicas': 'Básicas',
    # Quadril
    'quadril': 'Quadril',
    # Joelho
    'joelho': 'Joelho',
    # Ombro e cotovelo
    'ombro e cotovelo': 'Ombro e cotovelo', 'ombro': 'Ombro e cotovelo',
    'cotovelo': 'Ombro e cotovelo', 'ombro-cotovelo': 'Ombro e cotovelo',
    'ombro e cotovelol': 'Ombro e cotovelo',
    # Pé e tornozelo
    'pé e tornozelo': 'Pé e tornozelo', 'pe e tornozelo': 'Pé e tornozelo',
    'pé': 'Pé e tornozelo', 'pe': 'Pé e tornozelo',
    'tornozelo': 'Pé e tornozelo', 'pé/tornozelo': 'Pé e tornozelo',
    # Mão e punho
    'mão e punho': 'Mão e punho', 'mao e punho': 'Mão e punho',
    'mão': 'Mão e punho', 'mao': 'Mão e punho',
    'punho': 'Mão e punho', 'mão/punho': 'Mão e punho',
    # Coluna
    'coluna': 'Coluna',
    # Pediatria
    'pediatria': 'Pediatria', 'pediátrica': 'Pediatria',
    'ortopedia pediátrica': 'Pediatria',
    # Trauma
    'trauma': 'Trauma', 'traumatologia': 'Trauma',
    # Tumores
    'tumores': 'Tumores', 'tumor': 'Tumores',
    'oncologia': 'Tumores', 'oncológica': 'Tumores',
}


def normalize_category(cat_text: str) -> str:
    """Normaliza nome de categoria para o identificador oficial."""
    if not cat_text:
        return ''
    clean = cat_text.strip().lower()
    # Remove prefixes comuns
    for prefix in ['categoria:', 'cat:', 'cat ']:
        if clean.startswith(prefix):
            clean = clean[len(prefix):].strip()
    # Tenta match direto
    if clean in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[clean]
    # Tenta match parcial
    for alias, official in _CATEGORY_ALIASES.items():
        if alias in clean or clean in alias:
            return official
    # Tenta match com categorias oficiais (case insensitive)
    for cat in CATEGORIAS_OFICIAIS:
        if cat.lower() == clean:
            return cat
    return cat_text.strip()


# ============================================================
# TAXONOMIA COMPLETA
# Estrutura: { categoria: { subtema: { 'sub_subtemas': [...], 'ponte': [...], 'keywords': [...] } } }
# ============================================================
TAXONOMY = {
    'Básicas': {
        'Anatomia e embriologia musculoesquelética': {
            'sub_subtemas': ['Anatomia topográfica por segmento', 'Embriologia e desenvolvimento esquelético', 'Vascularização e inervação dos membros'],
            'ponte': [],
            'keywords': ['anatomia', 'embriologia', 'vascularização', 'inervação', 'topográfica', 'desenvolvimento esquelético'],
        },
        'Biologia óssea e consolidação': {
            'sub_subtemas': ['Histologia do osso, cartilagem e tendão', 'Consolidação primária e secundária', 'Fatores que retardam a consolidação'],
            'ponte': [],
            'keywords': ['biologia óssea', 'consolidação', 'histologia', 'cartilagem', 'tendão', 'osso'],
        },
        'Biomecânica e biomateriais': {
            'sub_subtemas': ['Princípios de carga, torção e cisalhamento', 'Biomateriais em ortopedia', 'Tribologia e desgaste'],
            'ponte': [],
            'keywords': ['biomecânica', 'biomateriais', 'tribologia', 'desgaste', 'polietileno', 'cerâmica', 'titânio', 'torção', 'cisalhamento'],
        },
        'Princípios de osteossíntese (AO)': {
            'sub_subtemas': ['Compressão, neutralização, ponte, proteção', 'Placas (DCP, LCP, bloqueadas)', 'Hastes intramedulares', 'Fixadores externos', 'Parafusos (cortical, esponjoso, bloqueado, canulado)'],
            'ponte': ['Trauma'],
            'keywords': ['osteossíntese', 'AO', 'placa', 'DCP', 'LCP', 'haste intramedular', 'fixador externo', 'parafuso', 'bloqueada', 'compressão', 'neutralização'],
        },
        'Semiologia e propedêutica geral': {
            'sub_subtemas': ['Exame físico por segmento', 'Sinais clínicos clássicos'],
            'ponte': [],
            'keywords': ['semiologia', 'propedêutica', 'exame físico', 'sinais clínicos'],
        },
        'Métodos de imagem': {
            'sub_subtemas': ['Radiografia', 'Tomografia computadorizada', 'Ressonância magnética', 'Ultrassonografia, cintilografia, PET'],
            'ponte': [],
            'keywords': ['radiografia', 'tomografia', 'ressonância', 'ultrassonografia', 'cintilografia', 'PET', 'imagem'],
        },
        'Doenças metabólicas ósseas': {
            'sub_subtemas': ['Osteoporose e fraturas por fragilidade', 'Osteomalácia e raquitismo', 'Doença de Paget', 'Osteodistrofia renal', 'Hiperparatireoidismo'],
            'ponte': ['Quadril', 'Coluna'],
            'keywords': ['metabólica', 'osteoporose', 'osteomalácia', 'raquitismo', 'Paget', 'osteodistrofia', 'hiperparatireoidismo', 'fragilidade'],
        },
        'Displasias esqueléticas': {
            'sub_subtemas': ['Acondroplasia', 'Osteogênese imperfeita', 'Exostose múltipla hereditária', 'Displasia epifisária múltipla'],
            'ponte': ['Pediatria'],
            'keywords': ['displasia esquelética', 'acondroplasia', 'osteogênese imperfeita', 'exostose múltipla', 'displasia epifisária'],
        },
        'Doenças reumatológicas': {
            'sub_subtemas': ['Artrite reumatoide (princípios)', 'Espondiloartropatias', 'Gota e artropatias microcristalinas', 'LES e vasculites'],
            'ponte': [],
            'keywords': ['reumatológica', 'artrite reumatoide', 'espondiloartropatia', 'gota', 'microcristalina', 'LES', 'vasculite'],
        },
        'Infecções osteoarticulares gerais': {
            'sub_subtemas': ['Osteomielite aguda e crônica', 'Artrite séptica', 'Tuberculose osteoarticular', 'Infecções fúngicas e atípicas'],
            'ponte': ['Trauma', 'Pediatria'],
            'keywords': ['infecção', 'osteomielite', 'artrite séptica', 'tuberculose osteoarticular', 'infecção fúngica'],
        },
        'Neuropatias e lesões nervosas': {
            'sub_subtemas': ['Classificação de Seddon e Sunderland', 'Reparo e enxerto nervoso', 'Neuropatias compressivas'],
            'ponte': [],
            'keywords': ['neuropatia', 'lesão nervosa', 'Seddon', 'Sunderland', 'enxerto nervoso', 'neuropraxia', 'axonotmese', 'neurotmese'],
        },
        'Farmacologia em ortopedia': {
            'sub_subtemas': ['AINEs, opioides, adjuvantes', 'Antibioticoterapia em infecção musculoesquelética', 'Bifosfonatos, denosumabe, teriparatida', 'Anticoagulantes e heparinas'],
            'ponte': [],
            'keywords': ['farmacologia', 'AINE', 'opioide', 'antibiótico', 'bifosfonato', 'denosumabe', 'teriparatida', 'anticoagulante', 'heparina'],
        },
        'Tromboprofilaxia e tromboembolismo venoso': {
            'sub_subtemas': ['Profilaxia em artroplastias', 'Profilaxia em trauma', 'Tratamento do TEV instalado'],
            'ponte': ['Quadril', 'Joelho'],
            'keywords': ['tromboprofilaxia', 'tromboembolismo', 'TEV', 'TVP', 'embolia pulmonar', 'profilaxia', 'trombose'],
        },
        'Anestesia, analgesia e reabilitação': {
            'sub_subtemas': ['Bloqueios regionais', 'Analgesia multimodal', 'Princípios de reabilitação e órteses'],
            'ponte': [],
            'keywords': ['anestesia', 'analgesia', 'bloqueio regional', 'reabilitação', 'órtese'],
        },
        'Ética, estatística e metodologia científica': {
            'sub_subtemas': ['Desenhos de estudo', 'Níveis de evidência', 'Ética em pesquisa e prática clínica'],
            'ponte': [],
            'keywords': ['ética', 'estatística', 'metodologia', 'evidência', 'desenho de estudo', 'metanálise', 'ensaio clínico'],
        },
    },

    'Quadril': {
        'Anatomia e biomecânica do quadril': {
            'sub_subtemas': ['Anatomia óssea e articular', 'Vascularização do colo femoral', 'Biomecânica da marcha e carga'],
            'ponte': [],
            'keywords': ['anatomia do quadril', 'colo femoral', 'biomecânica do quadril', 'marcha'],
        },
        'Acessos cirúrgicos do quadril': {
            'sub_subtemas': ['Anterior direto (Smith-Petersen / Hueter)', 'Anterolateral (Watson-Jones)', 'Lateral direto (Hardinge)', 'Posterior (Kocher-Langenbeck / Moore)', 'Acessos ao acetábulo (ilioinguinal, Stoppa)'],
            'ponte': [],
            'keywords': ['acesso', 'Smith-Petersen', 'Hueter', 'Watson-Jones', 'Hardinge', 'Kocher-Langenbeck', 'Moore', 'ilioinguinal', 'Stoppa', 'via de acesso'],
        },
        'Exame físico do quadril': {
            'sub_subtemas': ['Manobras clínicas clássicas', 'Semiologia da dor referida'],
            'ponte': [],
            'keywords': ['exame físico quadril', 'manobra', 'dor referida'],
        },
        'Imagem no quadril': {
            'sub_subtemas': ['Índices acetabulares e femorais', 'Ressonância e artro-ressonância', 'Tomografia e reconstruções 3D'],
            'ponte': [],
            'keywords': ['imagem quadril', 'índice acetabular', 'artro-ressonância'],
        },
        'Impacto femoroacetabular e lesões labrais': {
            'sub_subtemas': ['Impacto tipo CAM, pincer e misto', 'Lesões labrais', 'Tratamento artroscópico'],
            'ponte': [],
            'keywords': ['impacto femoroacetabular', 'IFA', 'CAM', 'pincer', 'labral', 'labrum', 'artroscopia do quadril'],
        },
        'Osteonecrose da cabeça femoral': {
            'sub_subtemas': ['Etiologia e fatores de risco', 'Classificações (Ficat, Steinberg, ARCO)', 'Tratamentos preservadores e artroplastia'],
            'ponte': ['Básicas'],
            'keywords': ['osteonecrose', 'necrose avascular', 'Ficat', 'Steinberg', 'ARCO', 'cabeça femoral'],
        },
        'Osteoartrose do quadril': {
            'sub_subtemas': ['Primária e secundária', 'Avaliação pré-operatória'],
            'ponte': [],
            'keywords': ['osteoartrose quadril', 'artrose do quadril', 'coxartrose'],
        },
        'Displasia acetabular residual do adulto': {
            'sub_subtemas': ['Diagnóstico no adulto jovem', 'Osteotomias periacetabulares'],
            'ponte': ['Pediatria'],
            'keywords': ['displasia acetabular', 'periacetabular', 'PAO'],
        },
        'Fraturas do acetábulo': {
            'sub_subtemas': ['Classificação de Letournel-Judet', 'Tratamento conservador versus cirúrgico', 'Vias de acesso aplicadas'],
            'ponte': ['Trauma'],
            'keywords': ['fratura acetábulo', 'Letournel', 'Judet', 'acetabular'],
        },
        'Fraturas do colo femoral': {
            'sub_subtemas': ['Classificação de Garden e Pauwels', 'Osteossíntese versus artroplastia', 'Complicações (necrose avascular, pseudartrose)'],
            'ponte': ['Trauma'],
            'keywords': ['fratura colo femoral', 'Garden', 'Pauwels', 'colo do fêmur'],
        },
        'Fraturas trocantéricas e subtrocantéricas': {
            'sub_subtemas': ['Classificação AO e de Evans', 'Haste cefalomedular versus DHS', 'Fraturas atípicas (associadas a bifosfonatos)'],
            'ponte': ['Trauma'],
            'keywords': ['trocantérica', 'subtrocantérica', 'Evans', 'DHS', 'haste cefalomedular', 'fratura atípica', 'bifosfonato'],
        },
        'Fraturas pélvicas': {
            'sub_subtemas': ['Classificação de Young-Burgess e Tile', 'Fixação externa e interna', 'Lesões associadas (urogenital e vascular)'],
            'ponte': ['Trauma'],
            'keywords': ['fratura pélvica', 'pelve', 'Young-Burgess', 'Tile', 'anel pélvico'],
        },
        'Luxações traumáticas do quadril': {
            'sub_subtemas': ['Luxação anterior e posterior', 'Fratura-luxação', 'Complicações'],
            'ponte': ['Trauma'],
            'keywords': ['luxação quadril', 'luxação do quadril', 'fratura-luxação'],
        },
        'Artroplastia total primária do quadril': {
            'sub_subtemas': ['Pares tribológicos', 'Fixação cimentada versus não-cimentada', 'Planejamento pré-operatório'],
            'ponte': [],
            'keywords': ['artroplastia quadril', 'ATQ', 'prótese quadril', 'tribológico', 'cimentada'],
        },
        'Revisão de artroplastia do quadril': {
            'sub_subtemas': ['Defeitos acetabulares (Paprosky)', 'Defeitos femorais (Paprosky, AAOS)', 'Técnicas de reconstrução'],
            'ponte': [],
            'keywords': ['revisão quadril', 'Paprosky', 'defeito acetabular', 'defeito femoral', 'revisão ATQ'],
        },
        'Complicações da artroplastia do quadril': {
            'sub_subtemas': ['Luxação protética', 'Soltura asséptica', 'Desgaste e osteólise', 'Fratura periprotética'],
            'ponte': [],
            'keywords': ['complicação artroplastia quadril', 'luxação protética', 'soltura asséptica', 'osteólise', 'fratura periprotética quadril'],
        },
        'Infecção periprotética': {
            'sub_subtemas': ['Critérios MSIS e ICM', 'Tratamento em um e dois tempos', 'DAIR'],
            'ponte': ['Básicas', 'Joelho'],
            'keywords': ['infecção periprotética', 'MSIS', 'ICM', 'DAIR', 'espaçador', 'dois tempos'],
        },
        'Osteotomias do quadril': {
            'sub_subtemas': ['Periacetabular (Ganz / PAO)', 'Varizantes e valgizantes femorais', 'Osteotomias de salvação'],
            'ponte': [],
            'keywords': ['osteotomia quadril', 'Ganz', 'varizante', 'valgizante'],
        },
        'Artrodese do quadril': {
            'sub_subtemas': ['Indicações atuais', 'Técnicas'],
            'ponte': [],
            'keywords': ['artrodese quadril'],
        },
        'Tendinopatias e bursites do quadril': {
            'sub_subtemas': ['Bursite trocantérica', 'Tendinopatia do iliopsoas', 'Lesões dos isquiotibiais proximais'],
            'ponte': [],
            'keywords': ['bursite trocantérica', 'tendinopatia iliopsoas', 'isquiotibiais', 'bursite quadril'],
        },
    },

    'Joelho': {
        'Anatomia e biomecânica do joelho': {
            'sub_subtemas': ['Anatomia ligamentar e meniscal', 'Cinemática femorotibial e femoropatelar'],
            'ponte': [],
            'keywords': ['anatomia joelho', 'cinemática', 'femorotibial', 'femoropatelar'],
        },
        'Acessos cirúrgicos do joelho': {
            'sub_subtemas': ['Parapatelar medial', 'Midvastus e subvastus', 'Acessos posteriores (Trickey, Burks-Schaffer)'],
            'ponte': [],
            'keywords': ['acesso joelho', 'parapatelar', 'midvastus', 'subvastus', 'Trickey'],
        },
        'Exame físico do joelho': {
            'sub_subtemas': ['Manobras ligamentares', 'Manobras meniscais', 'Avaliação patelofemoral'],
            'ponte': [],
            'keywords': ['exame físico joelho', 'Lachman', 'gaveta anterior', 'McMurray', 'Apley', 'pivot shift'],
        },
        'Imagem no joelho': {
            'sub_subtemas': ['Incidências especiais (Rosenberg, axial de patela)', 'Ressonância magnética', 'Tomografia com reconstrução'],
            'ponte': [],
            'keywords': ['imagem joelho', 'Rosenberg', 'axial patela'],
        },
        'Lesões meniscais': {
            'sub_subtemas': ['Padrões de lesão', 'Meniscectomia parcial, sutura, transplante'],
            'ponte': [],
            'keywords': ['menisco', 'meniscal', 'meniscectomia', 'sutura meniscal', 'transplante meniscal'],
        },
        'Lesão do ligamento cruzado anterior': {
            'sub_subtemas': ['Reconstrução (enxertos, túneis, fixação)', 'Associação com lesões complexas', 'Revisão de reconstrução'],
            'ponte': [],
            'keywords': ['LCA', 'cruzado anterior', 'ligamento cruzado anterior', 'reconstrução LCA', 'enxerto'],
        },
        'Lesão do ligamento cruzado posterior': {
            'sub_subtemas': ['Isolada e combinada', 'Reconstrução transtibial versus inlay'],
            'ponte': [],
            'keywords': ['LCP', 'cruzado posterior', 'ligamento cruzado posterior', 'transtibial', 'inlay'],
        },
        'Lesões colaterais e canto posterolateral': {
            'sub_subtemas': ['Ligamento colateral medial', 'Ligamento colateral lateral', 'Canto posterolateral'],
            'ponte': [],
            'keywords': ['colateral medial', 'colateral lateral', 'canto posterolateral', 'LCM', 'LCL', 'CPL'],
        },
        'Lesões multiligamentares': {
            'sub_subtemas': [],
            'ponte': [],
            'keywords': ['multiligamentar', 'múltiplos ligamentos'],
        },
        'Luxação do joelho': {
            'sub_subtemas': ['Avaliação vascular e neurológica', 'Estabilização primária', 'Reconstrução faseada'],
            'ponte': ['Trauma'],
            'keywords': ['luxação joelho', 'luxação do joelho'],
        },
        'Instabilidade femoropatelar e dor anterior': {
            'sub_subtemas': ['Fatores anatômicos predisponentes', 'Reconstrução do LPFM', 'Osteotomia da TAT (Fulkerson, Elmslie-Trillat)'],
            'ponte': [],
            'keywords': ['femoropatelar', 'instabilidade patelar', 'LPFM', 'Fulkerson', 'Elmslie-Trillat', 'dor anterior', 'luxação patela'],
        },
        'Lesões condrais e osteocondrais': {
            'sub_subtemas': ['Classificação de Outerbridge e ICRS', 'Microfratura, mosaicoplastia, implante condrocitário'],
            'ponte': [],
            'keywords': ['condral', 'osteocondral', 'Outerbridge', 'ICRS', 'microfratura', 'mosaicoplastia', 'condrocitário'],
        },
        'Osteocondrite dissecante': {
            'sub_subtemas': ['Juvenil versus adulto', 'Tratamento por estágio'],
            'ponte': ['Pediatria'],
            'keywords': ['osteocondrite dissecante', 'OCD'],
        },
        'Fraturas da patela': {
            'sub_subtemas': ['Obliquação em 8, parafusos', 'Patelectomia parcial e total'],
            'ponte': ['Trauma'],
            'keywords': ['fratura patela', 'patelectomia', 'fratura da patela'],
        },
        'Fraturas do platô tibial': {
            'sub_subtemas': ['Classificação de Schatzker e AO', 'Redução e fixação'],
            'ponte': ['Trauma'],
            'keywords': ['platô tibial', 'Schatzker', 'fratura platô'],
        },
        'Fraturas do fêmur distal': {
            'sub_subtemas': ['Classificação AO 33', 'Placa bloqueada versus haste retrógrada'],
            'ponte': ['Trauma'],
            'keywords': ['fêmur distal', 'fratura fêmur distal', 'haste retrógrada', 'AO 33'],
        },
        'Lesões tendíneas (quadricipital e patelar)': {
            'sub_subtemas': ['Ruptura aguda e crônica', 'Técnicas de reparo'],
            'ponte': [],
            'keywords': ['tendão quadricipital', 'tendão patelar', 'ruptura patelar', 'ruptura quadricipital'],
        },
        'Osteoartrose do joelho': {
            'sub_subtemas': ['Avaliação clínica e radiográfica', 'Tratamento conservador'],
            'ponte': [],
            'keywords': ['osteoartrose joelho', 'artrose joelho', 'gonartrose'],
        },
        'Osteotomias ao redor do joelho': {
            'sub_subtemas': ['Osteotomia tibial alta valgizante', 'Osteotomia femoral distal varizante', 'Princípios e indicações'],
            'ponte': [],
            'keywords': ['osteotomia joelho', 'osteotomia tibial alta', 'HTO', 'valgizante', 'varizante joelho'],
        },
        'Artroplastia unicompartimental': {
            'sub_subtemas': ['Indicações', 'Técnica e resultados'],
            'ponte': [],
            'keywords': ['unicompartimental', 'UKA'],
        },
        'Artroplastia total primária do joelho': {
            'sub_subtemas': ['Retenção versus substituição do cruzado posterior', 'Alinhamento mecânico versus cinemático', 'Balanço ligamentar'],
            'ponte': [],
            'keywords': ['artroplastia joelho', 'ATJ', 'prótese joelho', 'balanço ligamentar', 'alinhamento mecânico', 'alinhamento cinemático'],
        },
        'Revisão de artroplastia total do joelho': {
            'sub_subtemas': ['Defeitos ósseos (classificação AORI)', 'Constricções e hastes', 'Técnicas de reconstrução'],
            'ponte': [],
            'keywords': ['revisão joelho', 'AORI', 'revisão ATJ'],
        },
        'Complicações da artroplastia total do joelho': {
            'sub_subtemas': ['Rigidez', 'Soltura', 'Fratura periprotética'],
            'ponte': [],
            'keywords': ['complicação artroplastia joelho', 'rigidez joelho', 'fratura periprotética joelho'],
        },
        'Infecção periprotética do joelho': {
            'sub_subtemas': ['Critérios MSIS e ICM', 'Tratamento em um e dois tempos', 'DAIR'],
            'ponte': ['Básicas', 'Quadril'],
            'keywords': ['infecção periprotética joelho'],
        },
    },

    'Ombro e cotovelo': {
        'Anatomia e biomecânica do ombro e cintura escapular': {
            'sub_subtemas': ['Articulações glenoumeral, acromioclavicular, esternoclavicular e escapulotorácica', 'Biomecânica do arco de movimento'],
            'ponte': [],
            'keywords': ['anatomia ombro', 'glenoumeral', 'acromioclavicular', 'esternoclavicular', 'escapulotorácica'],
        },
        'Acessos cirúrgicos do ombro': {
            'sub_subtemas': ['Deltopeitoral', 'Superolateral (Neer)', 'Acessos posteriores'],
            'ponte': [],
            'keywords': ['acesso ombro', 'deltopeitoral', 'superolateral'],
        },
        'Exame físico do ombro': {
            'sub_subtemas': ['Manguito rotador', 'Instabilidade', 'Articulação acromioclavicular'],
            'ponte': [],
            'keywords': ['exame físico ombro', 'Jobe', 'Neer', 'Hawkins', 'apprehension'],
        },
        'Imagem no ombro': {
            'sub_subtemas': ['Incidências especiais (Grashey, axilar, Y)', 'Ressonância e artro-ressonância', 'Ultrassonografia dinâmica'],
            'ponte': [],
            'keywords': ['imagem ombro', 'Grashey', 'axilar', 'artro-ressonância ombro'],
        },
        'Instabilidade glenoumeral': {
            'sub_subtemas': ['Anterior (Bankart, reparos, Latarjet)', 'Posterior', 'Multidirecional', 'Perda óssea glenoidal e Hill-Sachs'],
            'ponte': [],
            'keywords': ['instabilidade glenoumeral', 'Bankart', 'Latarjet', 'Hill-Sachs', 'luxação ombro', 'instabilidade ombro'],
        },
        'Síndrome do impacto e lesões do manguito rotador': {
            'sub_subtemas': ['Síndrome do impacto (Neer)', 'Lesões parciais e completas', 'Reparo e transferências tendíneas'],
            'ponte': [],
            'keywords': ['manguito rotador', 'impacto', 'supraespinhal', 'infraespinhal', 'subescapular', 'reparo manguito', 'transferência tendínea'],
        },
        'Artropatia do manguito': {
            'sub_subtemas': ['Fisiopatologia', 'Artroplastia reversa como tratamento'],
            'ponte': [],
            'keywords': ['artropatia manguito', 'artroplastia reversa'],
        },
        'Tendinopatia bicipital e lesões SLAP': {
            'sub_subtemas': ['Tenotomia versus tenodese', 'Tipos de SLAP'],
            'ponte': [],
            'keywords': ['SLAP', 'bíceps', 'tenotomia', 'tenodese', 'bicipital'],
        },
        'Capsulite adesiva': {
            'sub_subtemas': ['Fases clínicas', 'Tratamento conservador e capsulotomia'],
            'ponte': [],
            'keywords': ['capsulite adesiva', 'ombro congelado', 'capsulotomia'],
        },
        'Osteoartrose e artropatias glenoumerais': {
            'sub_subtemas': ['Primária, pós-instabilidade, artrite reumatoide'],
            'ponte': [],
            'keywords': ['artrose ombro', 'osteoartrose glenoumeral'],
        },
        'Fraturas de úmero': {
            'sub_subtemas': ['Fraturas do úmero proximal (Neer)', 'Fraturas diafisárias do úmero', 'Fraturas do úmero distal'],
            'ponte': ['Trauma'],
            'keywords': ['fratura úmero', 'úmero proximal', 'diáfise úmero', 'úmero distal', 'Neer'],
        },
        'Fraturas da clavícula': {
            'sub_subtemas': ['Terços médio, lateral e medial'],
            'ponte': ['Trauma'],
            'keywords': ['fratura clavícula', 'clavícula'],
        },
        'Fraturas da escápula': {
            'sub_subtemas': ['Corpo, colo, glenoide e coracoide'],
            'ponte': ['Trauma'],
            'keywords': ['fratura escápula', 'escápula', 'glenoide', 'coracoide'],
        },
        'Lesões acromioclaviculares e esternoclaviculares': {
            'sub_subtemas': ['Classificação de Rockwood', 'Tratamento por grau'],
            'ponte': ['Trauma'],
            'keywords': ['acromioclavicular', 'esternoclavicular', 'Rockwood', 'luxação AC'],
        },
        'Artroplastia do ombro': {
            'sub_subtemas': ['Anatômica (hemi e total)', 'Reversa', 'Revisão'],
            'ponte': [],
            'keywords': ['artroplastia ombro', 'prótese ombro', 'hemiartroplastia ombro', 'reversa ombro'],
        },
        'Anatomia e biomecânica do cotovelo': {
            'sub_subtemas': ['Complexo ligamentar medial e lateral', 'Biomecânica do valgo e do varo'],
            'ponte': [],
            'keywords': ['anatomia cotovelo', 'biomecânica cotovelo'],
        },
        'Acessos cirúrgicos do cotovelo': {
            'sub_subtemas': ['Kocher, Kaplan, Hotchkiss e acesso posterior'],
            'ponte': [],
            'keywords': ['acesso cotovelo', 'Kocher', 'Kaplan', 'Hotchkiss'],
        },
        'Exame físico do cotovelo': {
            'sub_subtemas': ['Testes ligamentares'],
            'ponte': [],
            'keywords': ['exame físico cotovelo'],
        },
        'Epicondilites': {
            'sub_subtemas': ['Epicondilites medial e lateral', 'Tratamento conservador e cirúrgico'],
            'ponte': [],
            'keywords': ['epicondilite', 'cotovelo de tenista', 'cotovelo de golfista', 'epicôndilo'],
        },
        'Instabilidade do cotovelo': {
            'sub_subtemas': ['Instabilidade rotatória posterolateral', 'Colateral medial e valgo'],
            'ponte': [],
            'keywords': ['instabilidade cotovelo', 'PLRI', 'posterolateral cotovelo'],
        },
        'Rigidez e ossificação heterotópica': {
            'sub_subtemas': ['Prevenção e tratamento'],
            'ponte': [],
            'keywords': ['rigidez cotovelo', 'ossificação heterotópica'],
        },
        'Artrose e artropatias do cotovelo': {
            'sub_subtemas': ['Primária, pós-traumática, artrite reumatoide'],
            'ponte': [],
            'keywords': ['artrose cotovelo', 'artropatia cotovelo'],
        },
        'Fraturas do cotovelo': {
            'sub_subtemas': ['Fraturas da cabeça do rádio (Mason)', 'Fraturas do olécrano', 'Fraturas do coronoide', 'Tríade terrível', 'Fratura-luxação de Monteggia', 'Lesão de Essex-Lopresti'],
            'ponte': ['Trauma'],
            'keywords': ['fratura cotovelo', 'cabeça rádio', 'Mason', 'olécrano', 'coronoide', 'tríade terrível', 'Monteggia', 'Essex-Lopresti'],
        },
        'Artroplastia do cotovelo': {
            'sub_subtemas': ['Total, da cabeça do rádio', 'Indicações e complicações'],
            'ponte': [],
            'keywords': ['artroplastia cotovelo', 'prótese cotovelo', 'prótese cabeça rádio'],
        },
        'Neuropatias no cotovelo': {
            'sub_subtemas': ['Neuropatia ulnar (túnel cubital)', 'Neuropatia do interósseo posterior'],
            'ponte': [],
            'keywords': ['neuropatia ulnar', 'túnel cubital', 'interósseo posterior', 'nervo ulnar'],
        },
    },

    'Pé e tornozelo': {
        'Anatomia e biomecânica do pé e tornozelo': {
            'sub_subtemas': ['Arcos plantares, eixos do retropé', 'Marcha normal'],
            'ponte': [],
            'keywords': ['anatomia pé', 'anatomia tornozelo', 'arcos plantares', 'retropé'],
        },
        'Acessos cirúrgicos do pé e tornozelo': {
            'sub_subtemas': ['Anterior, posteromedial, posterolateral', 'Abordagens laterais estendidas'],
            'ponte': [],
            'keywords': ['acesso pé', 'acesso tornozelo'],
        },
        'Exame físico e biomecânica da marcha': {
            'sub_subtemas': ['Testes ligamentares e tendíneos', 'Análise da marcha patológica'],
            'ponte': [],
            'keywords': ['exame físico pé', 'exame físico tornozelo', 'marcha patológica'],
        },
        'Imagem do pé e tornozelo': {
            'sub_subtemas': ['Radiografia com carga', 'Ressonância, tomografia, cintilografia'],
            'ponte': [],
            'keywords': ['imagem pé', 'radiografia com carga'],
        },
        'Entorse e instabilidade lateral do tornozelo': {
            'sub_subtemas': ['Aguda e crônica', 'Reparo anatômico (Broström)'],
            'ponte': [],
            'keywords': ['entorse tornozelo', 'instabilidade lateral', 'Broström', 'ligamento talofibular'],
        },
        'Lesões do tendão de Aquiles': {
            'sub_subtemas': ['Ruptura aguda', 'Tendinopatias (inserional e não-inserional)'],
            'ponte': [],
            'keywords': ['Aquiles', 'tendão de Aquiles', 'ruptura Aquiles', 'tendinopatia Aquiles'],
        },
        'Disfunção do tibial posterior e pé plano adquirido do adulto': {
            'sub_subtemas': ['Classificação clínica (Myerson)', 'Tratamento por estágio'],
            'ponte': [],
            'keywords': ['tibial posterior', 'pé plano adquirido', 'Myerson', 'PPAA'],
        },
        'Lesões dos tendões fibulares': {
            'sub_subtemas': ['Rupturas, instabilidade, snapping'],
            'ponte': [],
            'keywords': ['tendão fibular', 'fibulares', 'snapping fibular'],
        },
        'Fasciíte plantar e entesopatias do calcâneo': {
            'sub_subtemas': ['Tratamento conservador e cirúrgico'],
            'ponte': [],
            'keywords': ['fasciíte plantar', 'fascite plantar', 'entesopatia calcâneo', 'esporão'],
        },
        'Hallux valgus': {
            'sub_subtemas': ['Avaliação de ângulos', 'Osteotomias (Chevron, Scarf, Akin, Lapidus)'],
            'ponte': [],
            'keywords': ['hallux valgus', 'joanete', 'Chevron', 'Scarf', 'Akin', 'Lapidus'],
        },
        'Hallux rigidus': {
            'sub_subtemas': ['Classificação', 'Queilectomia, osteotomia, artrodese'],
            'ponte': [],
            'keywords': ['hallux rigidus', 'queilectomia'],
        },
        'Deformidades dos dedos menores': {
            'sub_subtemas': ['Dedo em martelo, garra, mallet', 'Técnicas de correção'],
            'ponte': [],
            'keywords': ['dedo em martelo', 'dedo em garra', 'mallet toe', 'dedos menores'],
        },
        'Pé cavo': {
            'sub_subtemas': ['Etiologia neurológica', 'Correção cirúrgica'],
            'ponte': ['Pediatria'],
            'keywords': ['pé cavo', 'Charcot-Marie-Tooth'],
        },
        'Metatarsalgia e neuroma de Morton': {
            'sub_subtemas': ['Causas mecânicas', 'Tratamento'],
            'ponte': [],
            'keywords': ['metatarsalgia', 'neuroma de Morton', 'Morton'],
        },
        'Pé diabético e neuropatia de Charcot': {
            'sub_subtemas': ['Úlceras neuropáticas', 'Reconstrução do pé de Charcot'],
            'ponte': [],
            'keywords': ['pé diabético', 'Charcot', 'neuropatia diabética', 'úlcera neuropática'],
        },
        'Osteocondrites do pé': {
            'sub_subtemas': ['Doença de Freiberg', 'Doença de Köhler', 'Doença de Sever'],
            'ponte': ['Pediatria'],
            'keywords': ['Freiberg', 'Köhler', 'Sever', 'osteocondrite pé'],
        },
        'Lesões osteocondrais do tálus': {
            'sub_subtemas': ['Avaliação e tratamento'],
            'ponte': [],
            'keywords': ['osteocondral tálus', 'lesão tálus'],
        },
        'Artroses do pé e tornozelo': {
            'sub_subtemas': ['Primária e pós-traumática'],
            'ponte': [],
            'keywords': ['artrose tornozelo', 'artrose pé'],
        },
        'Artroplastia do tornozelo': {
            'sub_subtemas': ['Indicações e complicações'],
            'ponte': [],
            'keywords': ['artroplastia tornozelo', 'prótese tornozelo'],
        },
        'Artrodeses do pé e tornozelo': {
            'sub_subtemas': ['Tibiotalocalcaneana', 'Tríplice e duplas artrodeses', 'Antepé'],
            'ponte': [],
            'keywords': ['artrodese tornozelo', 'artrodese tríplice', 'tibiotalocalcaneana', 'artrodese pé'],
        },
        'Fraturas do tornozelo': {
            'sub_subtemas': ['Classificação de Weber e AO', 'Fraturas do pilão tibial'],
            'ponte': ['Trauma'],
            'keywords': ['fratura tornozelo', 'Weber', 'maléolo', 'pilão tibial', 'fratura bimaleolar', 'fratura trimaleolar'],
        },
        'Fraturas do tálus': {
            'sub_subtemas': ['Classificação de Hawkins', 'Complicações (necrose avascular)'],
            'ponte': ['Trauma'],
            'keywords': ['fratura tálus', 'Hawkins', 'tálus'],
        },
        'Fraturas do calcâneo': {
            'sub_subtemas': ['Classificação de Sanders', 'Acessos e fixação'],
            'ponte': ['Trauma'],
            'keywords': ['fratura calcâneo', 'Sanders', 'calcâneo'],
        },
        'Lesões tarsometatársicas (Lisfranc)': {
            'sub_subtemas': ['Diagnóstico e classificação', 'Fixação versus artrodese'],
            'ponte': ['Trauma'],
            'keywords': ['Lisfranc', 'tarsometatársica', 'lesão Lisfranc'],
        },
        'Fraturas dos metatarsais': {
            'sub_subtemas': ['Fratura de Jones e fraturas de estresse do 5º metatarso', 'Fraturas dos demais metatarsos'],
            'ponte': ['Trauma'],
            'keywords': ['fratura metatarso', 'fratura Jones', '5º metatarso', 'fratura de estresse'],
        },
    },

    'Mão e punho': {
        'Anatomia e biomecânica da mão e punho': {
            'sub_subtemas': ['Arcos do carpo, colunas do punho', 'Biomecânica flexora e extensora'],
            'ponte': [],
            'keywords': ['anatomia mão', 'anatomia punho', 'carpo', 'biomecânica mão'],
        },
        'Acessos cirúrgicos da mão e punho': {
            'sub_subtemas': ['Acessos dorsais e volares'],
            'ponte': [],
            'keywords': ['acesso mão', 'acesso punho'],
        },
        'Exame físico da mão e punho': {
            'sub_subtemas': ['Testes específicos (Finkelstein, Watson e outros)'],
            'ponte': [],
            'keywords': ['exame físico mão', 'Finkelstein', 'Watson', 'Allen'],
        },
        'Neuropatias compressivas': {
            'sub_subtemas': ['Síndrome do túnel do carpo', 'Túnel cubital', 'Canal de Guyon'],
            'ponte': [],
            'keywords': ['túnel do carpo', 'síndrome do túnel', 'Canal de Guyon', 'neuropatia compressiva mão'],
        },
        'Lesões tendíneas flexoras': {
            'sub_subtemas': ['Zonas de Verdan', 'Reparo e reabilitação'],
            'ponte': [],
            'keywords': ['tendão flexor', 'Verdan', 'zona flexora', 'flexor profundo', 'flexor superficial'],
        },
        'Lesões tendíneas extensoras': {
            'sub_subtemas': ['Dedo em martelo (mallet)', 'Deformidade em Boutonnière', 'Deformidade em Swan-neck', 'Zonas e técnicas'],
            'ponte': [],
            'keywords': ['tendão extensor', 'mallet finger', 'Boutonnière', 'Swan-neck', 'dedo em martelo mão'],
        },
        'Tenossinovites': {
            'sub_subtemas': ['Tenossinovite de De Quervain', 'Dedo em gatilho'],
            'ponte': [],
            'keywords': ['De Quervain', 'dedo em gatilho', 'tenossinovite', 'trigger finger'],
        },
        'Doença de Dupuytren': {
            'sub_subtemas': ['Estadiamento', 'Fasciectomia, agulha, colagenase'],
            'ponte': [],
            'keywords': ['Dupuytren', 'fasciectomia', 'contratura Dupuytren'],
        },
        'Fraturas do rádio distal': {
            'sub_subtemas': ['Classificação AO e de Fernandez', 'Tratamento conservador e cirúrgico'],
            'ponte': ['Trauma'],
            'keywords': ['fratura rádio distal', 'Fernandez', 'Colles', 'Smith', 'rádio distal'],
        },
        'Fratura do escafoide e demais carpais': {
            'sub_subtemas': ['Fraturas do escafoide (classificações e pseudartrose)', 'Fraturas dos demais ossos do carpo'],
            'ponte': ['Trauma'],
            'keywords': ['fratura escafoide', 'escafoide', 'pseudartrose escafoide', 'fratura carpal'],
        },
        'Instabilidades do carpo': {
            'sub_subtemas': ['SLAC e SNAC', 'DISI e VISI', 'Lesões escafossemilunares'],
            'ponte': [],
            'keywords': ['SLAC', 'SNAC', 'DISI', 'VISI', 'escafossemilunar', 'instabilidade carpal'],
        },
        'Lesão do TFCC e patologia ulnocarpal': {
            'sub_subtemas': ['Classificação de Palmer', 'Tratamento'],
            'ponte': [],
            'keywords': ['TFCC', 'fibrocartilagem triangular', 'Palmer', 'ulnocarpal'],
        },
        'Fraturas metacarpais e falangeanas': {
            'sub_subtemas': ['Fraturas metacarpais', 'Fraturas de falanges', 'Fratura do boxeador, Bennett, Rolando'],
            'ponte': ['Trauma'],
            'keywords': ['fratura metacarpo', 'fratura falange', 'Bennett', 'Rolando', 'boxeador'],
        },
        'Luxações das articulações da mão': {
            'sub_subtemas': ['Metacarpofalângica', 'Interfalângica proximal e distal'],
            'ponte': ['Trauma'],
            'keywords': ['luxação mão', 'metacarpofalângica', 'interfalângica'],
        },
        'Infecções da mão': {
            'sub_subtemas': ['Panarício, felon', 'Tenossinovite supurativa'],
            'ponte': ['Básicas'],
            'keywords': ['infecção mão', 'panarício', 'felon', 'tenossinovite supurativa'],
        },
        'Lesões vasculares e síndrome compartimental da mão': {
            'sub_subtemas': ['Fasciotomias', 'Lesões arteriais'],
            'ponte': ['Trauma'],
            'keywords': ['síndrome compartimental mão', 'fasciotomia mão', 'lesão vascular mão'],
        },
        'Amputações e replantes': {
            'sub_subtemas': ['Indicações e contraindicações', 'Técnica do replante'],
            'ponte': ['Trauma'],
            'keywords': ['amputação mão', 'replante', 'reimplante'],
        },
        'Rizartrose e artroses carpais': {
            'sub_subtemas': ['Classificação de Eaton', 'Artroplastias de suspensão'],
            'ponte': [],
            'keywords': ['rizartrose', 'Eaton', 'artrose trapéziometacarpal', 'artroplastia suspensão'],
        },
        'Artrite reumatoide da mão': {
            'sub_subtemas': ['Deformidades clássicas', 'Sinovectomia, artroplastias'],
            'ponte': ['Básicas'],
            'keywords': ['artrite reumatoide mão', 'deformidade mão reumatoide', 'sinovectomia mão'],
        },
        'Anomalias congênitas da mão': {
            'sub_subtemas': ['Polidactilia, sindactilia', 'Deficiências longitudinais'],
            'ponte': ['Pediatria'],
            'keywords': ['anomalia congênita mão', 'polidactilia', 'sindactilia'],
        },
        'Tumores e lesões ungueais': {
            'sub_subtemas': ['Cistos, tumores glômicos', 'Patologia ungueal cirúrgica'],
            'ponte': [],
            'keywords': ['tumor mão', 'tumor glômico', 'cisto mão', 'lesão ungueal'],
        },
    },

    'Coluna': {
        'Anatomia, biomecânica e vascularização da coluna': {
            'sub_subtemas': ['Cervical, torácica, lombar, sacral', 'Suprimento vascular medular'],
            'ponte': [],
            'keywords': ['anatomia coluna', 'vascularização medular', 'artéria de Adamkiewicz'],
        },
        'Exame neurológico e propedêutica': {
            'sub_subtemas': ['Níveis motores e sensitivos', 'Reflexos e sinais de neurônio motor superior e inferior'],
            'ponte': [],
            'keywords': ['exame neurológico', 'neurônio motor', 'reflexo', 'nível sensitivo', 'nível motor'],
        },
        'Imagem da coluna': {
            'sub_subtemas': ['Radiografia dinâmica, tomografia, ressonância', 'Mielo-tomografia'],
            'ponte': [],
            'keywords': ['imagem coluna', 'mielo-tomografia', 'radiografia dinâmica'],
        },
        'Acessos cirúrgicos da coluna': {
            'sub_subtemas': ['Anterior cervical, posterior cervical', 'Transtorácico, retroperitoneal', 'Lateral / transpsoas'],
            'ponte': [],
            'keywords': ['acesso coluna', 'transpsoas', 'retroperitoneal', 'anterior cervical'],
        },
        'Lombalgia e cervicalgia mecânicas': {
            'sub_subtemas': ['Diagnóstico diferencial e tratamento conservador'],
            'ponte': [],
            'keywords': ['lombalgia', 'cervicalgia', 'dor lombar', 'dor cervical'],
        },
        'Hérnia discal lombar': {
            'sub_subtemas': ['Clínica e imagem', 'Microdiscectomia e endoscopia'],
            'ponte': [],
            'keywords': ['hérnia discal lombar', 'ciática', 'microdiscectomia', 'disco lombar'],
        },
        'Hérnia discal cervical e radiculopatia': {
            'sub_subtemas': ['Abordagem anterior versus posterior'],
            'ponte': [],
            'keywords': ['hérnia discal cervical', 'radiculopatia cervical', 'disco cervical'],
        },
        'Estenose do canal lombar': {
            'sub_subtemas': ['Clínica (claudicação neurogênica)', 'Descompressão e fusão'],
            'ponte': [],
            'keywords': ['estenose lombar', 'claudicação neurogênica', 'estenose canal'],
        },
        'Mielopatia cervical espondilótica': {
            'sub_subtemas': ['Avaliação (escalas JOA, Nurick)', 'Laminoplastia, laminectomia, fusão'],
            'ponte': [],
            'keywords': ['mielopatia cervical', 'espondilótica', 'JOA', 'Nurick', 'laminoplastia'],
        },
        'Espondilólise e espondilolistese': {
            'sub_subtemas': ['Ístmica e degenerativa', 'Classificação de Meyerding', 'Fusão instrumentada'],
            'ponte': ['Pediatria'],
            'keywords': ['espondilólise', 'espondilolistese', 'Meyerding', 'ístmica'],
        },
        'Cifose de Scheuermann': {
            'sub_subtemas': ['Critérios diagnósticos', 'Tratamento ortopédico e cirúrgico'],
            'ponte': ['Pediatria'],
            'keywords': ['Scheuermann', 'cifose'],
        },
        'Escoliose idiopática': {
            'sub_subtemas': ['Infantil, juvenil, adolescente', 'Classificação de Lenke', 'Órtese e artrodese'],
            'ponte': ['Pediatria'],
            'keywords': ['escoliose idiopática', 'Lenke', 'escoliose adolescente'],
        },
        'Escoliose neuromuscular e sindrômica': {
            'sub_subtemas': ['Paralisia cerebral, distrofias, mielomeningocele', 'Desafios cirúrgicos'],
            'ponte': ['Pediatria'],
            'keywords': ['escoliose neuromuscular', 'escoliose sindrômica'],
        },
        'Deformidades do adulto e equilíbrio sagital': {
            'sub_subtemas': ['Parâmetros pélvicos e sagitais', 'Osteotomias (PSO, SPO)'],
            'ponte': [],
            'keywords': ['equilíbrio sagital', 'PSO', 'SPO', 'deformidade adulto', 'parâmetro pélvico', 'incidência pélvica'],
        },
        'Trauma cervical alto': {
            'sub_subtemas': ['Côndilo occipital, luxação occipitoatlantoide', 'Fratura de Jefferson (C1)', 'Fraturas do odontoide', 'Fratura de Hangman (C2)'],
            'ponte': ['Trauma'],
            'keywords': ['trauma cervical alto', 'Jefferson', 'odontoide', 'Hangman', 'C1', 'C2', 'atlas', 'áxis'],
        },
        'Trauma cervical subaxial': {
            'sub_subtemas': ['Classificação SLIC / AO', 'Luxação facetária'],
            'ponte': ['Trauma'],
            'keywords': ['trauma cervical subaxial', 'SLIC', 'facetária', 'cervical subaxial'],
        },
        'Trauma toracolombar': {
            'sub_subtemas': ['Classificação TLICS / AO', 'Fraturas por compressão, burst, flexão-distração, luxação'],
            'ponte': ['Trauma'],
            'keywords': ['trauma toracolombar', 'TLICS', 'burst', 'flexão-distração', 'fratura torácica', 'fratura lombar'],
        },
        'Lesão medular traumática': {
            'sub_subtemas': ['Escala ASIA', 'Manejo agudo e prognóstico'],
            'ponte': ['Trauma'],
            'keywords': ['lesão medular', 'ASIA', 'medula espinhal', 'paraplegia', 'tetraplegia'],
        },
        'Fraturas osteoporóticas da coluna': {
            'sub_subtemas': ['Vertebroplastia, cifoplastia', 'Tratamento conservador'],
            'ponte': ['Básicas', 'Trauma'],
            'keywords': ['fratura osteoporótica coluna', 'vertebroplastia', 'cifoplastia', 'fratura vertebral'],
        },
        'Infecções da coluna': {
            'sub_subtemas': ['Espondilodiscite', 'Abscesso epidural', 'Mal de Pott'],
            'ponte': ['Básicas'],
            'keywords': ['infecção coluna', 'espondilodiscite', 'abscesso epidural', 'Pott', 'tuberculose coluna'],
        },
        'Tumores da coluna': {
            'sub_subtemas': ['Primários (cordoma, osteoma osteoide)', 'Metastáticos (Tokuhashi, SINS)'],
            'ponte': ['Tumores'],
            'keywords': ['tumor coluna', 'cordoma', 'Tokuhashi', 'SINS', 'metástase coluna'],
        },
        'Complicações em cirurgia da coluna': {
            'sub_subtemas': ['Falhas de instrumental', 'Síndrome do segmento adjacente', 'Fístula liquórica'],
            'ponte': [],
            'keywords': ['complicação coluna', 'segmento adjacente', 'fístula liquórica', 'falha instrumental'],
        },
    },

    'Pediatria': {
        'Desenvolvimento esquelético normal': {
            'sub_subtemas': ['Núcleos de ossificação', 'Variações do normal'],
            'ponte': [],
            'keywords': ['desenvolvimento esquelético', 'núcleo de ossificação', 'ossificação', 'variação do normal'],
        },
        'Marcha pediátrica': {
            'sub_subtemas': ['Marcha normal e patológica', 'Claudicações na infância'],
            'ponte': [],
            'keywords': ['marcha pediátrica', 'claudicação infância', 'marcha criança'],
        },
        'Fraturas fisárias': {
            'sub_subtemas': ['Classificação de Salter-Harris', 'Epifisiodese pós-traumática'],
            'ponte': ['Trauma'],
            'keywords': ['fratura fisária', 'Salter-Harris', 'fise', 'epifisiodese', 'placa de crescimento'],
        },
        'Displasia do desenvolvimento do quadril': {
            'sub_subtemas': ['Triagem e diagnóstico', 'Pavlik, redução fechada e aberta', 'Osteotomias pélvicas e femorais'],
            'ponte': ['Quadril'],
            'keywords': ['DDQ', 'displasia desenvolvimento', 'Pavlik', 'Ortolani', 'Barlow', 'displasia quadril'],
        },
        'Doença de Legg-Calvé-Perthes': {
            'sub_subtemas': ['Classificação (Catterall, Herring)', 'Contenção e osteotomias'],
            'ponte': ['Quadril'],
            'keywords': ['Perthes', 'Legg-Calvé-Perthes', 'Catterall', 'Herring'],
        },
        'Epifisiólise proximal do fêmur': {
            'sub_subtemas': ['Estável e instável', 'Fixação in situ'],
            'ponte': ['Quadril'],
            'keywords': ['epifisiólise', 'SCFE', 'epifisiólise femoral'],
        },
        'Pé torto congênito': {
            'sub_subtemas': ['Método Ponseti', 'Cirurgia em falhas de tratamento'],
            'ponte': ['Pé e tornozelo'],
            'keywords': ['pé torto', 'Ponseti', 'pé torto congênito', 'equinovaro'],
        },
        'Pé plano e pé cavo pediátricos': {
            'sub_subtemas': ['Flexível versus rígido', 'Indicações cirúrgicas'],
            'ponte': ['Pé e tornozelo'],
            'keywords': ['pé plano pediátrico', 'pé cavo pediátrico', 'pé plano infantil'],
        },
        'Torcicolo muscular congênito': {
            'sub_subtemas': ['Tratamento conservador e cirúrgico'],
            'ponte': [],
            'keywords': ['torcicolo congênito', 'torcicolo muscular'],
        },
        'Deformidades angulares e rotacionais dos MMII': {
            'sub_subtemas': ['Doença de Blount', 'Anteversão femoral aumentada', 'Geno varo e geno valgo fisiológicos'],
            'ponte': [],
            'keywords': ['Blount', 'anteversão femoral', 'geno varo', 'geno valgo', 'deformidade angular', 'tíbia vara'],
        },
        'Discrepância de membros inferiores': {
            'sub_subtemas': ['Etiologias e cálculo', 'Epifisiodese e alongamento'],
            'ponte': [],
            'keywords': ['discrepância', 'alongamento', 'epifisiodese membros'],
        },
        'Doenças neuromusculares': {
            'sub_subtemas': ['Paralisia cerebral', 'Distrofias musculares', 'Atrofia muscular espinhal, mielomeningocele'],
            'ponte': [],
            'keywords': ['paralisia cerebral', 'distrofia muscular', 'Duchenne', 'mielomeningocele', 'atrofia muscular espinhal'],
        },
        'Artrogripose': {
            'sub_subtemas': ['Tipos e manejo'],
            'ponte': [],
            'keywords': ['artrogripose'],
        },
        'Osteocondroses': {
            'sub_subtemas': ['Osgood-Schlatter', 'Sinding-Larsen-Johansson', 'Sever', 'Köhler e Freiberg', 'Panner'],
            'ponte': [],
            'keywords': ['osteocondrose', 'Osgood-Schlatter', 'Sinding-Larsen', 'Panner'],
        },
        'Infecções osteoarticulares pediátricas': {
            'sub_subtemas': ['Osteomielite aguda hematogênica', 'Artrite séptica', 'Sinovite transitória do quadril'],
            'ponte': ['Básicas'],
            'keywords': ['infecção pediátrica', 'osteomielite pediátrica', 'artrite séptica criança', 'sinovite transitória'],
        },
        'Tumores pediátricos do sistema musculoesquelético': {
            'sub_subtemas': ['Particularidades pediátricas'],
            'ponte': ['Tumores'],
            'keywords': ['tumor pediátrico', 'tumor infantil'],
        },
        'Fraturas pediátricas específicas': {
            'sub_subtemas': ['Fraturas supracondilianas do úmero', 'Fraturas do cotovelo pediátrico', 'Fraturas de Monteggia e Galeazzi pediátricas', 'Fraturas do fêmur na criança'],
            'ponte': ['Trauma', 'Ombro e cotovelo'],
            'keywords': ['fratura supracondiliana', 'fratura pediátrica', 'fratura criança', 'cotovelo pediátrico', 'Galeazzi pediátrica'],
        },
        'Lesão não-acidental': {
            'sub_subtemas': ['Sinais de alarme', 'Conduta legal e médica'],
            'ponte': [],
            'keywords': ['lesão não-acidental', 'abuso infantil', 'maus-tratos'],
        },
        'Reabilitação e aparelhos em pediatria': {
            'sub_subtemas': ['Gessos, órteses', 'Princípios específicos'],
            'ponte': [],
            'keywords': ['reabilitação pediátrica', 'gesso pediátrico', 'órtese pediátrica'],
        },
    },

    'Trauma': {
        'Atendimento ao politraumatizado': {
            'sub_subtemas': ['ATLS aplicado à ortopedia', 'Controle de danos ortopédico'],
            'ponte': [],
            'keywords': ['politraumatizado', 'ATLS', 'controle de danos', 'damage control'],
        },
        'Fraturas expostas': {
            'sub_subtemas': ['Classificação de Gustilo-Anderson', 'Desbridamento, antibioticoterapia, cobertura'],
            'ponte': ['Básicas'],
            'keywords': ['fratura exposta', 'Gustilo', 'Gustilo-Anderson', 'fratura aberta'],
        },
        'Síndrome compartimental': {
            'sub_subtemas': ['Diagnóstico e fasciotomia', 'Sequelas'],
            'ponte': ['Básicas'],
            'keywords': ['síndrome compartimental', 'fasciotomia', 'pressão compartimental'],
        },
        'Complicações sistêmicas do trauma ortopédico': {
            'sub_subtemas': ['Embolia gordurosa', 'Rabdomiólise e esmagamento', 'Tromboembolismo pós-trauma'],
            'ponte': [],
            'keywords': ['embolia gordurosa', 'rabdomiólise', 'esmagamento', 'complicação sistêmica trauma'],
        },
        'Lesões vasculares em trauma ortopédico': {
            'sub_subtemas': ['Luxação do joelho, supracondiliana', 'Reparo e fasciotomia profilática'],
            'ponte': [],
            'keywords': ['lesão vascular trauma', 'lesão arterial', 'reparo vascular'],
        },
        'Lesões nervosas periféricas em trauma': {
            'sub_subtemas': ['Diagnóstico', 'Tempo de exploração cirúrgica'],
            'ponte': ['Básicas'],
            'keywords': ['lesão nervosa trauma', 'neuropraxia', 'exploração nervosa'],
        },
        'Princípios biomecânicos de osteossíntese': {
            'sub_subtemas': ['Remissão aos sub-subtemas de Básicas'],
            'ponte': ['Básicas'],
            'keywords': ['princípio osteossíntese'],
        },
        'Fraturas diafisárias de ossos longos sem categoria regional dedicada': {
            'sub_subtemas': ['Diáfise femoral', 'Diáfise tibial'],
            'ponte': [],
            'keywords': ['diáfise femoral', 'diáfise tibial', 'fratura diafisária fêmur', 'fratura diafisária tíbia'],
        },
        'Luxações maiores e fratura-luxações': {
            'sub_subtemas': ['Agrupamento transversal'],
            'ponte': ['Quadril', 'Joelho', 'Ombro e cotovelo'],
            'keywords': ['luxação maior', 'fratura-luxação'],
        },
        'Retardo de consolidação e pseudartrose': {
            'sub_subtemas': ['Pseudartrose atrófica, hipertrófica, infectada', 'Enxertia, haste de troca, BMP'],
            'ponte': ['Básicas'],
            'keywords': ['pseudartrose', 'retardo consolidação', 'BMP', 'enxerto ósseo', 'não-união'],
        },
        'Consolidação viciosa': {
            'sub_subtemas': ['Osteotomias corretivas'],
            'ponte': [],
            'keywords': ['consolidação viciosa', 'osteotomia corretiva'],
        },
        'Infecção pós-traumática e osteomielite crônica': {
            'sub_subtemas': ['Classificação de Cierny-Mader', 'Técnica de Masquelet e transporte ósseo'],
            'ponte': ['Básicas'],
            'keywords': ['infecção pós-traumática', 'Cierny-Mader', 'Masquelet', 'transporte ósseo'],
        },
        'Fraturas patológicas': {
            'sub_subtemas': ['Avaliação e fixação profilática', 'Escores prognósticos (Mirels)'],
            'ponte': ['Tumores'],
            'keywords': ['fratura patológica', 'Mirels', 'fixação profilática'],
        },
        'Amputações traumáticas': {
            'sub_subtemas': ['Níveis e reabilitação', 'Replante (seleção de casos)'],
            'ponte': [],
            'keywords': ['amputação traumática', 'replante'],
        },
        'Lesões por arma branca e arma de fogo': {
            'sub_subtemas': ['Manejo das lesões por projétil', 'Extração de projéteis'],
            'ponte': [],
            'keywords': ['arma de fogo', 'projétil', 'PAF', 'arma branca'],
        },
        'Trauma no idoso': {
            'sub_subtemas': ['Fraturas por fragilidade', 'Ortogeriatria'],
            'ponte': [],
            'keywords': ['trauma idoso', 'ortogeriatria', 'fragilidade'],
        },
    },

    'Tumores': {
        'Princípios de oncologia musculoesquelética': {
            'sub_subtemas': ['Biologia tumoral', 'Avaliação clínica'],
            'ponte': [],
            'keywords': ['oncologia musculoesquelética', 'biologia tumoral'],
        },
        'Estadiamento': {
            'sub_subtemas': ['Sistema de Enneking', 'AJCC'],
            'ponte': [],
            'keywords': ['estadiamento', 'Enneking', 'AJCC'],
        },
        'Biópsia em tumores musculoesqueléticos': {
            'sub_subtemas': ['Por agulha versus incisional', 'Armadilhas e princípios'],
            'ponte': [],
            'keywords': ['biópsia tumor', 'biópsia óssea', 'biópsia musculoesquelética'],
        },
        'Imagem em tumores musculoesqueléticos': {
            'sub_subtemas': ['Radiografia, ressonância, tomografia, cintilografia', 'PET-CT'],
            'ponte': [],
            'keywords': ['imagem tumor', 'PET-CT'],
        },
        'Tumores ósseos formadores de osso': {
            'sub_subtemas': ['Osteoma osteoide', 'Osteoblastoma', 'Osteossarcoma'],
            'ponte': [],
            'keywords': ['osteoma osteoide', 'osteoblastoma', 'osteossarcoma', 'formador de osso'],
        },
        'Tumores ósseos formadores de cartilagem': {
            'sub_subtemas': ['Osteocondroma', 'Encondroma e doença de Ollier', 'Condroblastoma, fibroma condromixoide', 'Condrossarcoma'],
            'ponte': [],
            'keywords': ['osteocondroma', 'encondroma', 'Ollier', 'condroblastoma', 'condrossarcoma', 'formador de cartilagem'],
        },
        'Tumor de células gigantes': {
            'sub_subtemas': ['Tratamento cirúrgico', 'Denosumabe'],
            'ponte': [],
            'keywords': ['tumor de células gigantes', 'TCG', 'células gigantes'],
        },
        'Lesões ósseas císticas': {
            'sub_subtemas': ['Cisto ósseo simples', 'Cisto ósseo aneurismático'],
            'ponte': [],
            'keywords': ['cisto ósseo', 'cisto unicameral', 'cisto aneurismático'],
        },
        'Tumores fibrosos e histiocíticos': {
            'sub_subtemas': ['Displasia fibrosa', 'Fibroma não-ossificante', 'Histiocitose de células de Langerhans'],
            'ponte': [],
            'keywords': ['displasia fibrosa', 'fibroma não-ossificante', 'Langerhans', 'histiocitose'],
        },
        'Sarcoma de Ewing e PNET': {
            'sub_subtemas': ['Diagnóstico e tratamento multimodal'],
            'ponte': [],
            'keywords': ['Ewing', 'PNET', 'sarcoma de Ewing'],
        },
        'Cordoma e adamantinoma': {
            'sub_subtemas': ['Localizações típicas', 'Princípios cirúrgicos'],
            'ponte': [],
            'keywords': ['cordoma', 'adamantinoma'],
        },
        'Mieloma múltiplo e linfoma ósseo': {
            'sub_subtemas': ['Diagnóstico e manejo ortopédico'],
            'ponte': [],
            'keywords': ['mieloma', 'linfoma ósseo', 'mieloma múltiplo'],
        },
        'Metástases ósseas': {
            'sub_subtemas': ['Escores prognósticos (Mirels, Tokuhashi, SINS)', 'Manejo cirúrgico'],
            'ponte': ['Coluna', 'Trauma'],
            'keywords': ['metástase óssea', 'metástase', 'Tokuhashi', 'SINS', 'Mirels'],
        },
        'Tumores benignos de partes moles': {
            'sub_subtemas': ['Lipoma, schwannoma, neurofibroma', 'Hemangioma, glomus'],
            'ponte': [],
            'keywords': ['lipoma', 'schwannoma', 'neurofibroma', 'hemangioma', 'tumor benigno partes moles'],
        },
        'Sarcomas de partes moles': {
            'sub_subtemas': ['Princípios de ressecção', 'Margens oncológicas'],
            'ponte': [],
            'keywords': ['sarcoma partes moles', 'margem oncológica', 'ressecção tumoral'],
        },
        'Tumor desmoide e fibromatoses': {
            'sub_subtemas': ['Comportamento biológico', 'Tratamento multimodal'],
            'ponte': [],
            'keywords': ['desmoide', 'fibromatose'],
        },
        'Cirurgia oncológica ortopédica': {
            'sub_subtemas': ['Margens, biópsia prévia', 'Reconstrução (endoprótese, aloenxerto, biológica)', 'Amputação oncológica'],
            'ponte': [],
            'keywords': ['cirurgia oncológica', 'endoprótese', 'aloenxerto', 'amputação oncológica'],
        },
        'Terapia adjuvante e neoadjuvante': {
            'sub_subtemas': ['Princípios de quimioterapia e radioterapia', 'Integração com cirurgia'],
            'ponte': [],
            'keywords': ['quimioterapia', 'radioterapia', 'adjuvante', 'neoadjuvante'],
        },
        'Complicações em ortopedia oncológica': {
            'sub_subtemas': ['Hipercalcemia', 'Fratura patológica', 'Recidiva local'],
            'ponte': [],
            'keywords': ['hipercalcemia', 'recidiva local', 'complicação oncológica'],
        },
    },
}


# ============================================================
# ENGINE DE MATCHING LOCAL
# ============================================================

def _normalize_text(text: str) -> str:
    """Normaliza texto para matching (lowercase, remove acentos comuns)."""
    if not text:
        return ''
    t = text.lower().strip()
    # Normalizar acentos comuns para facilitar matching
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
        'é': 'e', 'ê': 'e',
        'í': 'i',
        'ó': 'o', 'ô': 'o', 'õ': 'o',
        'ú': 'u', 'ü': 'u',
        'ç': 'c',
    }
    for old, new in replacements.items():
        t = t.replace(old, new)
    return t


def _build_keyword_index():
    """Constrói índice invertido: keyword → [(categoria, subtema, peso)]."""
    index = {}
    for cat, subtemas in TAXONOMY.items():
        for sub_name, sub_data in subtemas.items():
            # Keywords explícitas (peso alto)
            for kw in sub_data.get('keywords', []):
                nkw = _normalize_text(kw)
                if nkw not in index:
                    index[nkw] = []
                index[nkw].append((cat, sub_name, 3.0))

            # Sub-subtemas como keywords (peso médio)
            for ss in sub_data.get('sub_subtemas', []):
                nss = _normalize_text(ss)
                if nss not in index:
                    index[nss] = []
                index[nss].append((cat, sub_name, 2.0))

            # Nome do subtema como keyword (peso médio)
            nsn = _normalize_text(sub_name)
            if nsn not in index:
                index[nsn] = []
            index[nsn].append((cat, sub_name, 2.5))

    return index


# Índice pré-construído (singleton)
_KEYWORD_INDEX = _build_keyword_index()


def suggest_classification(
    enunciado: str,
    alternativas: str = '',
    categoria_atual: str = '',
    resolucao: str = '',
) -> dict:
    """
    Sugere classificação (categoria + subtema) baseado no conteúdo da questão.

    Retorna: {
        'categoria': str,
        'subtema': str,
        'sub_subtema': str,  # melhor match se encontrado
        'confidence': float,  # 0.0 a 1.0
        'method': 'local',
    }
    """
    # Texto completo para análise
    full_text = _normalize_text(f'{enunciado} {alternativas} {resolucao}')

    if not full_text.strip():
        return {
            'categoria': normalize_category(categoria_atual) or '',
            'subtema': '',
            'sub_subtema': '',
            'confidence': 0.0,
            'method': 'local',
        }

    # Normalizar categoria atual
    cat_norm = normalize_category(categoria_atual)

    # Score de cada (categoria, subtema) baseado em keyword matches
    scores = {}  # (cat, subtema) → score

    for keyword, entries in _KEYWORD_INDEX.items():
        # Verificar se a keyword aparece no texto
        if keyword in full_text:
            # Bonus por match exato de palavras inteiras (não substring)
            # Ex: "LCA" deve ter bonus vs "placa"
            word_bonus = 1.0
            if len(keyword) <= 4:
                # Keywords curtas: verificar se é palavra inteira
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, full_text):
                    word_bonus = 2.0
                else:
                    word_bonus = 0.3  # Substring match de keyword curta = pouco confiável

            for cat, sub_name, weight in entries:
                key = (cat, sub_name)
                if key not in scores:
                    scores[key] = 0.0
                scores[key] += weight * word_bonus

                # Bonus se a categoria atual bate
                if cat_norm and cat == cat_norm:
                    scores[key] += 1.0

    if not scores:
        return {
            'categoria': cat_norm or '',
            'subtema': '',
            'sub_subtema': '',
            'confidence': 0.0,
            'method': 'local',
        }

    # Ordenar por score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_key, best_score = ranked[0]
    best_cat, best_sub = best_key

    # Se a categoria atual é válida e o melhor match está em outra categoria,
    # verificar se há um match razoável na categoria atual
    if cat_norm and best_cat != cat_norm:
        cat_matches = [(k, s) for k, s in ranked if k[0] == cat_norm]
        if cat_matches:
            cat_key, cat_score = cat_matches[0]
            # Se o match na categoria atual é pelo menos 60% do melhor, preferir
            if cat_score >= best_score * 0.6:
                best_key = cat_key
                best_score = cat_score
                best_cat, best_sub = best_key

    # Calcular confidence (normalizada)
    max_possible = 30.0  # Score teórico máximo razoável
    confidence = min(best_score / max_possible, 1.0)

    # Tentar encontrar o sub-subtema mais específico
    best_sub_subtema = ''
    if best_cat in TAXONOMY and best_sub in TAXONOMY[best_cat]:
        sub_data = TAXONOMY[best_cat][best_sub]
        best_ss_score = 0
        for ss in sub_data.get('sub_subtemas', []):
            nss = _normalize_text(ss)
            if nss in full_text:
                score = len(nss)
                if score > best_ss_score:
                    best_ss_score = score
                    best_sub_subtema = ss

    return {
        'categoria': best_cat,
        'subtema': best_sub,
        'sub_subtema': best_sub_subtema,
        'confidence': round(confidence, 2),
        'method': 'local',
    }


def get_subtemas_for_category(categoria: str) -> list:
    """Retorna lista de subtemas para uma categoria (para dropdowns)."""
    cat = normalize_category(categoria)
    if cat in TAXONOMY:
        return list(TAXONOMY[cat].keys())
    return []


def get_sub_subtemas(categoria: str, subtema: str) -> list:
    """Retorna lista de sub-subtemas para um subtema."""
    cat = normalize_category(categoria)
    if cat in TAXONOMY and subtema in TAXONOMY[cat]:
        return TAXONOMY[cat][subtema].get('sub_subtemas', [])
    return []


def get_all_categories() -> list:
    """Retorna lista de categorias oficiais."""
    return list(CATEGORIAS_OFICIAIS)
