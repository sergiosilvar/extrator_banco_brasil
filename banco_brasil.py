import locale
import pandas as pd
import re
import unicodedata
from itertools import zip_longest
from pathlib import Path
import logging
import numpy as np

logger = logging.getLogger(__name__)

locale.setlocale( locale.LC_ALL, 'pt_BR' )

CSV_DIR_EXTRATO_CC = '/Users/sergio/Google Drive/Financas/Banco do Brasil/Extratos Conta Corrente'
CSV_DIR_EXTRATO_FUNDO_INVESTIMENTO = '/Users/sergio/Google Drive/Financas/Banco do Brasil/Extratos Fundos de Investimento'
TXT_DIR_BRASILPREV = '/Users/sergio/Google Drive/Financas/Banco do Brasil/Extrato BrasilPrev'

def converte_moeda(dataframe):
    '''
    Esta implementação preguiçosa tenta converter todas as colunas de um objeto
    pandas.Dataframe que contém valores numéricos no formato brasileiro (por
    exemplo, "1.234.567,890", onde o spearador de milhar é o ponto e o
    separador decimal é a vírgula) para o tipo numpy.float64. Também converte
    para float64 colunas com números inteiros.
    As que não podem ser convertidas por não serem numéricas ou não estarem no
    formato acima tem sua exceção de erro silenciada.

    Parâmetros
    ----------
    dataframe - Um objeto pandas.Dataframe.

    '''

    for column in dataframe.columns.tolist():
        try:
            dataframe[column] = \
                dataframe[column].astype(str).apply(locale.atof)
        except ValueError:
            pass
    return dataframe

def remove_acentuacao(s, encoding='latin-1'):
    '''
    Troca caracteres acentuados de código "latin-1" por não acentuados. Testado
    apenas para encoding 'latin-1'. Um encoding diferente lançará uma exceção.
    Exemplo: ã -> a, È -> e, Ç -> Ç.

    Parâmetros
    ----------
    s - string a com caracteres acentuados a ser convertidos.
    encoding (default 'latin-1')- código unicode da string "s".
    '''
    if encoding != 'latin-1':
        raise NotImplementedError('Este método foi implementado e testado '+
            'apenas para encoding = "latin-1".')
    nfkd_form = unicodedata.normalize('NFKD', s)
    return nfkd_form.encode(encoding, 'ignore').decode(encoding)

def _trata_df_extrato_cc(dataframe, ignora_saldo=True):
    '''
    Método auxliar fazer os ajustes necessários em um objeto pandas.DataFrame
    criado diretamente  dos conteúdos de extratos de conta corrente em arquivos
    CSV:
        - Colunas adicionais para o dia, mês e ano dos lançamentos;
        - Campo data no formato DD/MM/YYYY.
        - Remoção de acentuação e lower case no histórico para processamento de
            texto;
        - Coluna para a hora do lançamento, quando houver.

    Retorna um pandas.DataFrame com todos os ajustes realizados.

    Parâmetros
    ----------
    dataframe - Objeto pandas.DataFrame criado diretamente de um extrato em
        arquivo CSV.
    ignora_saldo (default True) - Se True, ignora as linhas de saldo do extrato.
    '''

    dataframe.columns = ['Data','Origem','Historico','DataBalancete','Documento',
        'Valor','Excluir']
    del dataframe['Excluir']

    dataframe.Historico = dataframe.Historico.str.lower().apply(remove_acentuacao)
    dataframe.Documento = dataframe.Documento.astype(str)
    dataframe['Data'] = dataframe.Data.apply(lambda x: x[-4:]+'-'+x[-10:-8]+'-'+x[-7:-5])
    dataframe['AnoMes'] = dataframe.Data.apply(lambda x: x[:4]+'-'+x[5:7])
    dataframe['Mes'] = dataframe.Data.apply(lambda x: x[5:7]).astype(int)
    dataframe['Ano'] = dataframe.Data.apply(lambda x: x[:4]).astype(int)
    dataframe.sort_values('Data', inplace=True)

    # Corrigir Data para lançamentos que possuem data e hora no histórico.
    dia_hora = dataframe.Historico.str.extract(r'(\d{2}/\d{2})\s(\d{2}:\d{2})?',
        expand=True)

    dia_hora.columns = ['Dia', 'Hora']
    dataframe['Hora'] = dia_hora.Hora
    dataframe['DiaMes'] = dia_hora.Dia

    # TODO: Criar coluna como int, mesmo com NaN.
    dataframe['Dia'] = dia_hora.Dia.str[:2].apply(lambda x: int(x)
        if not pd.isnull(x) else np.NaN)


    def corrigir_data(x):
        if pd.notnull(x.DiaMes):
            m,d = x.DiaMes[-2:], x.DiaMes[:2]
            y = x.Data[:4]
            ymd = '{}-{}-{}'.format(y,m,d)
            return ymd
        return x.Data
    dataframe['Data'] = dataframe.apply(corrigir_data, axis=1)
    del dia_hora, dataframe['DiaMes']

    # Dia da semana.
#    def dia_semana(x):
    semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
#        return semana[x]
    dataframe['DiaSemana'] = pd.to_datetime(dataframe.Data).apply(
        lambda x:  semana[x.dayofweek])

    if ignora_saldo:
        #ignore_historico = ['saldo', 's a l d o']
        ignore_index = dataframe.Historico.str.contains('s\s*a\s*\l\s*d\s*o',
            regex=True)
        dataframe = dataframe[~ignore_index]

    dataframe.index = range(len(dataframe))
    return dataframe

def compila_conta_corrente(pasta=CSV_DIR_EXTRATO_CC, ignora_saldo=True):
    '''
    Compila extratos de conta corrente em arquivos CSV para um objeto
    pandas.DataFrame.  Os extratos devem estar em um único diretório e no
    formato CSV emitidos no site do Banco do Brasil.

    Parâmetros
    ----------
    pasta - Pasta com todos os arquivos CSV.
    ignora_saldo (default True) - Se True, ignora as linhas de saldo do extrato.
    '''

    path = Path(pasta)

    # Não há problemas em converter para uma lista, não serão muitos arquivos.
    csv_files = list(path.glob('*.csv'))
    logger.debug('{} arquivos CSV encontrados em {}.'.format(len(csv_files),
        path.absolute().as_posix()))

    csv_df = [pd.DataFrame.from_csv(i.as_posix(),
        encoding='latin-1', index_col=None) for i in csv_files]

    df = pd.concat(csv_df)

    return _trata_df_extrato_cc(df, ignora_saldo)

__re_brl = '(-?(?:\d{1,3}\.)?(?:\d{1,3})+(?:\,\d{2}))'
__regex_saldo_anterior = re.compile('SALDO ANTERIOR\s+{}'.format(__re_brl))
__regex_saldo_atual = re.compile(r'SALDO ATUAL\s+=\s+{}'.format(__re_brl))
__regex_rend_bruto = re.compile(r'RENDIMENTO BRUTO\s+\([\+|-]\)\s+{}'.format(__re_brl))
__regex_rend_liquido = re.compile(r'RENDIMENTO L[IÍ]QUIDO\s+{}'.format(__re_brl))
__regex_resgate = re.compile(r'RESGATES\s+\(\-\)\s+{}'.format(__re_brl))
__regex_imp_renda = re.compile(r'IMPOSTO DE RENDA\s+\(\-\)\s+{}'.format(__re_brl))
__regex_imp_iof = re.compile(r'IOF\s+\(\-\)\s+{}'.format(__re_brl))
__regex_aplicacoes = re.compile(r'APLICA[CÇ][OÕ]ES\s+\(\+\)\s+{}'.format(__re_brl))
__regex_titulo = re.compile(r'BB (.*?)\s+(?:- CNPJ:)?\s+(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})')
__regex_ano_mes = re.compile(r'\d{2}/(\d{2})/(\d{4})\s?SALDO ATUAL')


def _processa_extrato_fundo_investimento(texto):
    # Split the file into records.
    #matches = re.finditer('BB .* - CNPJ:', texto
    texto = remove_acentuacao(texto.upper())
    matches = __regex_titulo.finditer(texto)
    start_record = [r.start() for r in matches]
    end_record = start_record.copy()
    end_record.remove(end_record[0])
    records = map(lambda pos:texto[pos[0]:pos[1]], zip_longest(start_record,end_record))

    monthly_book = []

    # Process each record...
    for rec in records:

        monthly_statement = {}

        #monthly_statement['Mes'] = re.search('(\d{4}-\d{2})', nome_arquivo).groups()[0]
        mes, ano = __regex_ano_mes.search(rec).groups()
        monthly_statement['Mes'] = '{}-{}'.format(ano, mes)

        monthly_statement['Fundo'] = __regex_titulo.search(rec).groups()[0]

        # "DIVIDA EXTERN MIL" e "REF DI LP 250 MIL" foram renomeados em 2016-05.
        if monthly_statement['Fundo'] == 'DIVIDA EXTERN MIL':
            monthly_statement['Fundo'] = 'RF DIVIDA EXT MIL'
        elif monthly_statement['Fundo'] == 'REF DI LP 250 MIL':
            monthly_statement['Fundo'] = 'RF REF DI 250 MIL'


        #logger.debug('Processando Fundo de Investimento "{}-{}"'.format(monthly_statement['Mes'], monthly_statement['Fundo']))

        try:
            monthly_statement['Saldo_anterior'] = __regex_saldo_anterior.search(rec).groups()[0]
            monthly_statement['Saldo_atual'] = __regex_saldo_atual.search(rec).groups()[0]
            monthly_statement['Rend_bruto'] = __regex_rend_bruto.search(rec).groups()[0]
            monthly_statement['Rend_liquido'] = __regex_rend_liquido.search(rec).groups()[0]
            monthly_statement['Retirada'] = __regex_resgate.search(rec).groups()[0]
            monthly_statement['IR'] = __regex_imp_renda.search(rec).groups()[0]
            monthly_statement['IOF'] = __regex_imp_iof.search(rec).groups()[0]
            monthly_statement['Aplicacao'] = __regex_aplicacoes.search(rec).groups()[0]
        except Exception as e:
            logger.error('Erro em {}-{}: {}'.format(ano, mes, e))
            raise e
        #print(monthly_statement)
        #break
        monthly_book.append(monthly_statement)
    return monthly_book


def compila_fundo_investimento(pasta=CSV_DIR_EXTRATO_FUNDO_INVESTIMENTO):

    book = []

    path = Path(pasta)
    csv_files = path.glob('*.txt')
    files = [i.as_posix() for i in csv_files]

    for fname in files[:]:

        with open(fname, 'r', encoding='latin-1') as f:
            texto = f.read()
            texto = remove_acentuacao(texto)
            texto = texto.upper()

            book.extend(_processa_extrato_fundo_investimento(texto))


    df = pd.DataFrame(book)
    col_names = df.columns.tolist()
    col_names.remove('Fundo')
    col_names.insert(0, 'Fundo')
    df = df[col_names]

    df = converte_moeda(df)
    return df


def compila_brasilprev(pasta=TXT_DIR_BRASILPREV):

    path = Path(TXT_DIR_BRASILPREV)
    txt_files = [i.as_posix() for i in path.glob('*.txt')]

    re_brl = '(-?(?:\d{1,3}\.)?(?:\d{1,3})+(?:\,\d{2}))'

    book = []


    # Seção HISTÓRICO DA MOVIMENTAÇÃO
    s = 'SALDO ANTERIOR DA PROVISAO\s+RT FIX V FIC\s+{}\s+{}'.format(re_brl, re_brl)
    re_saldo_anterior_rt_fix = re.compile(s)

    s = 'SALDO ANTERIOR DA PROVISAO\s+RT COMPOSTO RV 20 V FIC\s+{}\s+{}'.format(re_brl, re_brl)
    re_saldo_anterior_rt_composto = re.compile(s)

    s = 'CONTRIBUICAO PERIODICA BRUTA APOSENTADORIA\s+RT FIX V FIC\s+{}\s+{}'.format(re_brl, re_brl)
    re_contrib_per_rt_fix = re.compile(s)

    s = 'CONTRIBUICAO PERIODICA BRUTA APOSENTADORIA\s+RT COMPOSTO RV 20 V FIC\s+{}\s+{}'.format(re_brl, re_brl)
    re_contrib_per_rt_composto = re.compile(s)

    s = 'CONTRIBUICAO ESPORADICA BRUTA\s+RT FIX V FIC\s+{}\s+{}'.format(re_brl, re_brl)
    re_contrib_esp_rt_fix = re.compile(s)

    s = 'CONTRIBUICAO ESPORADICA BRUTA\s+RT COMPOSTO RV 20 V FIC\s+{}\s+{}'.format(re_brl, re_brl)
    re_contrib_esp_rt_composto = re.compile(s)

    s = 'SALDO ATUAL DA PROVISAO\s+RT FIX V FIC\s+{}\s+{}'.format(re_brl, re_brl)
    re_saldo_atual_rt_fix = re.compile(s)

    s = 'SALDO ATUAL DA PROVISAO\s+RT COMPOSTO RV 20 V FIC\s+{}\s+{}'.format(re_brl, re_brl)
    re_saldo_atual_rt_composto = re.compile(s)

    s = 'RENDIMENTO ACUMULADO NO PER[A-Z]+:\s+{}'.format(re_brl)
    re_rend_acumulado = re.compile(s)


    # Seção RENDIMENTO POR FUNDO. Pegar valores na coluna PARTICIPANTE.
    s = 'RENDIMENTO POR FUNDO.*RT FIX V FIC\s+\d{2}\s+'+re_brl+'.*RT COMPOSTO RV 20 V FIC\s+\d{2}\s+'+re_brl
    re_rendimento_fundo = re.compile(s, re.DOTALL)



    for fname in txt_files[:]:

        with open(fname, 'r', encoding='latin-1') as f:
            text = f.read()
            text = remove_acentuacao(text)
            text = text.upper()



        # Store all information.
        monthly_statement = {}

        re_brl = '(-?(?:\d{1,3}\.)?(?:\d{1,3})+(?:\,\d{2}))'

        groups = re_saldo_anterior_rt_fix.search(text).groups()
        monthly_statement['FIX_SldAnt_Cts'] = groups[0]
        monthly_statement['FIX_SldAnt_Vlr'] = groups[1]

        groups = re_saldo_anterior_rt_composto.search(text).groups()
        monthly_statement['COMP_SldAnt_Cts'] = groups[0]
        monthly_statement['COMP_SldAnt_Vlr'] = groups[1]

        m = re_contrib_per_rt_fix.search(text)
        if m:
            groups = m.groups()
            monthly_statement['FIX_ContrPer_Cts'] = groups[0]
            monthly_statement['FIX_ContrPer_Vlr'] = groups[1]

        m = re_contrib_per_rt_composto.search(text)
        if m:
            groups = m.groups()
            monthly_statement['COMP_ContrPer_Cts'] = groups[0]
            monthly_statement['COMP_ContrPer_Vlr'] = groups[1]

        m = re_contrib_esp_rt_fix.search(text)
        if m:
            groups = m.groups()
            monthly_statement['FIX_ContrEsp_Cts'] = groups[0]
            monthly_statement['FIX_ContrEsp_Vlr'] = groups[1]

        m = re_contrib_esp_rt_composto.search(text)
        if m:
            groups = m.groups()
            monthly_statement['COMP_ContrEsp_Cts'] = groups[0]
            monthly_statement['COMP_ContrEsp_Vlr'] = groups[1]

        groups = re_saldo_atual_rt_fix.search(text).groups()
        monthly_statement['FIX_SldAtual_Cts'] = groups[0]
        monthly_statement['FIX_SldAtual_Vlr'] = groups[1]

        groups = re_saldo_atual_rt_composto.search(text).groups()
        monthly_statement['COMP_SldAtual_Cts'] = groups[0]
        monthly_statement['COMP_SldAtual_Vlr'] = groups[1]

        groups = re_rend_acumulado.search(text).groups()
        monthly_statement['Rend'] = groups[0]

        groups = re_rendimento_fundo.search(text).groups()
        monthly_statement['FIX_Rend'] = groups[0]
        monthly_statement['COMP_Rend'] = groups[1]

        monthly_statement['Mes'] = re.search('(\d{4}-\d{2})', fname).groups()[0]

        book.append(monthly_statement)

    df = pd.DataFrame(book)
    col_names = df.columns.tolist()
    df = df[col_names]

    df = converte_moeda(df)

    return df
