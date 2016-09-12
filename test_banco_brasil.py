import unittest
import pandas as pd
import banco_brasil as bb
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TestExtratorBancoBrasil(unittest.TestCase):


    def test_converte_float(self):
        df = pd.DataFrame(
            {
                'numero_pt_br': # Esta coluna será convertida para float.
                    [
                        '0', ',0', '0,1', '1234,567', '1.234,56789',
                        '1.234.567,89','1.234.567.890,12'
                    ],

                'numero_en_us': # Esta coluna NÃO será convertida para float.
                    [
                        '0', '.0', '0.1', '1234.567', '1,234.56789',
                        '1,234,567.89','1,234,567,890.12'
                    ],

                'numero_int': # Esta coluna será convertida para float.
                    [
                        '1', '23', '456', '7890', '12345678', '0', '0'
                    ],

                'string': # Esta coluna não será convertida para float.
                    [
                        'a', 'bc', 'cde', 'fghi', 'jklmn', 'opqrst', 'x'
                    ]
            }
        )
        df2 = bb.converte_moeda(df)
        self.assertEqual(df2.numero_pt_br.dtype, np.float64)
        self.assertEqual(df2.numero_en_us.dtype, np.object)
        self.assertEqual(df2.numero_int.dtype, np.float64)
        self.assertEqual(df2.string.dtype, np.object)

    def test_remove_acentuacao(self):
        self.assertEqual(bb.remove_acentuacao('áÊïÕùç'),'aEiOuc')
        with  self.assertRaises(NotImplementedError):
            bb.remove_acentuacao('à', 'utf-8')

    def test_compila_conta_corrente(self):
        df = bb.compila_conta_corrente('./test_data/extrato_conta_corrente',
            ignora_saldo = False)
        self.assertEqual(len(df), 22)

        df = bb.compila_conta_corrente('./test_data/extrato_conta_corrente')
        self.assertEqual(len(df), 18)

        cols = ['Data', 'Origem', 'Historico', 'DataBalancete', 'Documento',
            'Valor', 'AnoMes', 'Ano', 'Mes', 'Dia', 'Hora', 'DiaSemana']
        self.assertEqual(set(df.columns.tolist()), set(cols))

        self.assertEqual(df.Valor.dtype, np.float64)

        self.assertEqual(df.Ano.dtype, np.int64)

        self.assertEqual(df.Mes.dtype, np.int64)

        self.assertEqual(df.Dia.dtype, np.float64)

        semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
        self.assertTrue(df.DiaSemana.isin(semana).all())

        self.assertTrue(df.AnoMes.str.match('^[0-9]{4}-[0-9]{2}$').all())

        self.assertTrue(df.Data.str.match(
            '^[12][09][0-9]{2}-[01][0-9]-[0123][0-9]').all())

        self.assertTrue(df.Hora[~df.Hora.isnull()].str.match(
            '^[012][0-9]:[012345][0-9]$').all())

    def test__processa_extrato_fundo_investimento(self):
        from pathlib import Path
        teste_path = './test_data/extrato_fundo_investimento/'
        path = Path(teste_path)
        f =  open(path.joinpath('2016-06.txt').as_posix(), 'r', encoding='latin-1')
        text = f.read()
        dicts = bb._processa_extrato_fundo_investimento(text)
        QTD_REGISTROS = 2
        self.assertEqual(len(dicts), QTD_REGISTROS)

        first = dicts[0]
        campos = set(['Fundo', 'Mes', 'Saldo_anterior', 'Saldo_atual', 'Rend_bruto',
            'Rend_liquido', 'Retirada', 'IR', 'IOF', 'Aplicacao'])
        self.assertEqual(set(first.keys()), campos)

        SALDO_ATUAL_PRIMEIRO_REGISTRO = '1.334,56'
        self.assertEqual(SALDO_ATUAL_PRIMEIRO_REGISTRO, first['Saldo_atual'])

        second = dicts[1]
        REND_LIQUIDO_SEGUNDO_REGISTRO = '1.375,25'
        self.assertEqual(REND_LIQUIDO_SEGUNDO_REGISTRO, second['Rend_liquido'])

    def test_compila_fundo_investimento(self):
        from pathlib import Path
        teste_path = './test_data/extrato_fundo_investimento'
        df = bb.compila_fundo_investimento(teste_path)

        QTD_REGISTROS = 4
        self.assertEqual(QTD_REGISTROS, len(df))

        NOME_FUNDOS = set(['RF REF DI', 'RF DIVIDA EXT MIL'])
        self.assertEqual(NOME_FUNDOS, set(df.Fundo.unique().tolist()))

        SOMA_SALDO_ATUAL_REF_DI = 11363.79 + 11364.89
        g = df.groupby('Fundo')
        soma = g.sum().loc['RF REF DI']['Saldo_atual']
        self.assertEqual(SOMA_SALDO_ATUAL_REF_DI, soma)






if __name__ == '__main__':
    unittest.main()
