# Modifications summary:
# - Inject `ex:hasContent` triple for statutes by extracting the body of the chunk
# - Do NOT preprocess/stem here; backend will do it at runtime

import os
import re
import asyncio
from pathlib import Path
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, XSD, OWL
from googletrans import Translator

# ─── Directories ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
SRC_ROOT = BASE_DIR / 'chunks'
OUTPUT   = BASE_DIR / 'knowledge_graph.ttl'

# ─── Namespaces ────────────────────────────────────────────────────────────────
EX     = Namespace('http://example.org/traffic-law#')
SCHEMA = Namespace('http://schema.org/')

# ─── Initialize graph and translator ────────────────────────────────────────────
g = Graph()
g.bind('ex', EX)
g.bind('schema', SCHEMA)
translator = Translator()

async def _translate(text: str, src: str, dest: str) -> str:
    result = await translator.translate(text, src=src, dest=dest)
    return result.text

def translate_sync(text: str, src: str, dest: str) -> str:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        return asyncio.run(_translate(text, src, dest))
    else:
        return loop.run_until_complete(_translate(text, src, dest))

def add_multilang_label(node, text):
    g.add((node, RDFS.label, Literal(text, lang='ms')))
    g.add((node, RDFS.label, Literal(translate_sync(text, 'ms', 'en'), lang='en')))
    g.add((node, RDFS.label, Literal(translate_sync(text, 'ms', 'zh-cn'), lang='zh')))

def parse_metadata(text: str) -> dict:
    meta = {}
    last_key = None
    for line in text.splitlines():
        if not line.strip():
            break
        if line.startswith('#'):
            inner = line[1:].strip()
            if ':' in inner:
                key, val = inner.split(':', 1)
                key, val = key.strip(), val.strip()
                meta[key] = val
                last_key = key
            elif last_key:
                meta[last_key] += ' ' + inner
        elif last_key:
            meta[last_key] += ' ' + line.strip()
    return meta

# ─── Ontology Declarations ─────────────────────────────────────────────────────
g.add((EX.Penalty, RDF.type, OWL.Class))
g.add((EX.amount, RDF.type, OWL.DatatypeProperty))
g.add((EX.currency, RDF.type, OWL.DatatypeProperty))
g.add((EX.duration, RDF.type, OWL.DatatypeProperty))
g.add((EX.hasPenalty, RDF.type, OWL.ObjectProperty))
g.add((EX.hasPenalty, RDFS.domain, EX.Statute))
g.add((EX.hasPenalty, RDFS.domain, EX.RegulationEntry))
g.add((EX.hasPenalty, RDFS.range, EX.Penalty))
g.add((EX.Offense, RDF.type, OWL.Class))
g.add((EX.offenseType, RDF.type, OWL.ObjectProperty))
g.add((EX.offenseType, RDFS.domain, EX.RegulationEntry))
g.add((EX.offenseType, RDFS.range, EX.Offense))

# ─── Graph Construction ────────────────────────────────────────────────────────
for subdir, _, files in os.walk(SRC_ROOT):
    folder = Path(subdir).name
    for fn in files:
        if not fn.lower().endswith('.txt'):
            continue
        path = Path(subdir) / fn
        content = path.read_text(encoding='utf-8')
        if '\n\n' in content:
            meta_text, body = content.split('\n\n', 1)
        else:
            meta_text, body = content, ''
        body = body.strip().replace('"', '\"')
        data = parse_metadata(meta_text)
        subj = None

        if data.get('type') == 'statute':
            src = data.get('source', '').replace(' ', '_')
            sec = data.get('section', '')
            subj = EX[f'statute_{src}_sec_{sec}']
            g.add((subj, RDF.type, EX.Statute))
            g.add((subj, EX.sectionNumber, Literal(sec)))
            if body:
                g.add((subj, EX.hasContent, Literal(body)))  # ✅ Inject raw body for model
            fine_val = data.get('fine')
            if fine_val and fine_val.lower() != 'none':
                pen = EX[f'penalty_statute_{src}_sec_{sec}_fine']
                g.add((pen, RDF.type, EX.Penalty))
                g.add((pen, EX.amount, Literal(fine_val)))
                g.add((pen, EX.currency, Literal('MYR')))
                g.add((subj, EX.hasPenalty, pen))
                add_multilang_label(pen, fine_val)
            jail_val = data.get('jail_term')
            if jail_val and jail_val.lower() != 'none':
                pen_j = EX[f'penalty_statute_{src}_sec_{sec}_jail']
                g.add((pen_j, RDF.type, EX.Penalty))
                g.add((pen_j, EX.duration, Literal(jail_val)))
                g.add((subj, EX.hasPenalty, pen_j))
                add_multilang_label(pen_j, jail_val)

        elif data.get('type') == 'regulation':
            src = Path(data.get('source', '')).stem
            item = data.get('item', '')
            subj = EX[f'reg_{src}_item_{item}']
            g.add((subj, RDF.type, EX.RegulationEntry))
            g.add((subj, SCHEMA.name, Literal(data.get('regulation', ''))))
            for period in ('1_15', '16_30', '31_60'):
                key = f'fine_{period}_days'
                amt = data.get(key)
                if amt:
                    pen = EX[f'penalty_{src}_{item}_{period}']
                    g.add((pen, RDF.type, EX.Penalty))
                    g.add((pen, EX.amount, Literal(amt, datatype=XSD.decimal)))
                    g.add((pen, EX.currency, Literal('MYR')))
                    g.add((subj, EX.hasPenalty, pen))
            jp = data.get('jail_possible')
            if jp and jp.lower() != 'tidak':
                pen_j = EX[f'jail_penalty_{src}_{item}']
                g.add((pen_j, RDF.type, EX.Penalty))
                g.add((pen_j, EX.duration, Literal(jp)))
                g.add((subj, EX.hasPenalty, pen_j))
            imp = data.get('implements_section') or data.get('regulation_section')
            if imp:
                sid = re.sub(r'[^\w]', '_', imp)
                g.add((subj, EX.implementsSection, EX[f'statute_Akta_333_sec_{sid}']))
            off = data.get('offense')
            if off:
                oid = re.sub(r'\W+', '_', off)
                off_uri = EX[f'offense_{oid}']
                g.add((off_uri, RDF.type, EX.Offense))
                add_multilang_label(off_uri, off)
                g.add((subj, EX.offenseType, off_uri))

        elif data.get('type') == 'handbook':
            src = Path(data.get('source', '')).stem
            mod = data.get('module', '')
            subj = EX[f'handbook_{src}_mod_{mod}']
            g.add((subj, RDF.type, EX.HandbookModule))

        elif folder == 'news_articles':
            art_id = data.get('id')
            subj = EX[f'news_article_{art_id}']
            g.add((subj, RDF.type, EX.NewsArticle))
            if data.get('url'):
                g.add((subj, SCHEMA.url, Literal(data.get('url'))))

        if subj and data.get('title'):
            add_multilang_label(subj, data['title'])
        if subj and data.get('source'):
            g.add((subj, EX.sourceFile, Literal(data.get('source'))))

# ─── Serialize graph ──────────────────────────────────────────────────────────
g.serialize(destination=str(OUTPUT), format='turtle')
print(f"✅ Knowledge graph written to {OUTPUT}")










