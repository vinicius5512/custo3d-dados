"""Baixa da ANEEL as tarifas residenciais (B1 convencional) vigentes de todas as
distribuidoras e a bandeira tarifária mais recente. Grava dados/tarifas.json.
Roda no GitHub Actions toda semana (workflow tarifas.yml)."""
import json, time, urllib.parse, urllib.request, datetime, sys

BASE = 'https://dadosabertos.aneel.gov.br/api/3/action/datastore_search?'
TARIFAS = 'fcf2906c-7c32-4b9b-a637-054e7a5234f4'
BANDEIRA = '0591b8f6-fe54-437b-b72b-1aa2efd46e42'

def get(params, tentativas=6):
    err = None
    for i in range(tentativas):
        try:
            req = urllib.request.Request(BASE + urllib.parse.urlencode(params), headers={'User-Agent': 'Mozilla/5.0 Custo3D'})
            j = json.load(urllib.request.urlopen(req, timeout=60))
            if j.get('success'): return j['result']
            err = j.get('error')
        except Exception as e:
            err = e
        time.sleep(min(30, 3 * 2 ** i))
    raise RuntimeError(f'ANEEL falhou: {err}')

def num(v):
    s = str(v or '').strip()
    if ',' in s: s = s.replace('.', '').replace(',', '.')
    return float(s or 0)

hoje = datetime.date.today().isoformat()
agentes = [r['SigAgente'] for r in get({'resource_id': TARIFAS, 'fields': 'SigAgente', 'distinct': 'true', 'limit': 1000})['records']]
dist = {}
for a in agentes:
    try:
        recs = get({'resource_id': TARIFAS, 'limit': 10, 'sort': 'DatInicioVigencia desc', 'filters': json.dumps({
            'SigAgente': a, 'DscSubGrupo': 'B1', 'DscModalidadeTarifaria': 'Convencional', 'DscBaseTarifaria': 'Tarifa de Aplicação',
            'DscSubClasse': 'Residencial', 'DscDetalhe': 'Não se aplica'})})['records']
    except Exception as e:
        print('erro', a, e); continue
    recs = [r for r in recs if r['DatInicioVigencia'] <= hoje and (r.get('DscUnidadeTerciaria') or 'MWh') == 'MWh']
    if not recs: continue
    vig = [r for r in recs if (r.get('DatFimVigencia') or '9999') >= hoje] or recs
    r = vig[0]
    dist[a] = [round(num(r['VlrTUSD']), 2), round(num(r['VlrTE']), 2), r['DatInicioVigencia'], r.get('DatFimVigencia') or '']

if len(dist) < 50:
    sys.exit(f'Poucas distribuidoras ({len(dist)}), mantendo arquivo anterior')

b = get({'resource_id': BANDEIRA, 'limit': 3, 'sort': 'DatCompetencia desc'})['records']
bandeira = None
if b:
    x = b[0]
    bandeira = {'comp': x['DatCompetencia'][:7], 'nome': x['NomBandeiraAcionada'], 'adicional': num(x.get('VlrAdicionalBandeira'))}

json.dump({'gerado': hoje, 'unidade': 'R$/MWh', 'bandeira': bandeira, 'dist': dist},
          open('dados/tarifas.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('ok', len(dist), 'distribuidoras; bandeira', bandeira)
