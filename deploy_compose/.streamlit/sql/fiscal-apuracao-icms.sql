-- Connect to MySQL database
USE autogeral;

select b.CFOP_EMPRESA CFOP
     , SUM(VALOR_TOTAL_BRUTO) valor_contabil
     , SUM(ICMS_BASE_EMPRESA) base_icms
     , SUM(ICMS_VALOR_EMPRESA) valor_icms
  from compras_dbf a join compras_itens_dbf b on a.compra=b.compra and a.loja=b.loja
 where a.cadastro between '2024-02-01 00:00:00' and '2024-03-01 00:00:00'
   and a.loja=10
 group by b.CFOP_EMPRESA;


select c.TIPO
     , c.LOJA
     , c.CODIGO
     , b.DESCRICAO_SIMPLIFICADA
     , c.QUANTIDADE*c.VALOR_UNIDADE valor_contabil
     , CASE WHEN c.TIPO='NFE' THEN d.CFOP
            WHEN c.TIPO='SAT' THEN e.CFOP
            WHEN c.TIPO='NFCE' THEN f.CFOP
            ELSE 0
		END CFOP
     , CASE WHEN c.TIPO='NFE' THEN d.BASE_ICMS_VALOR
            WHEN c.TIPO='SAT' THEN e.BASE_ICMS_VALOR
            WHEN c.TIPO='NFCE' THEN f.BASE_ICMS_VALOR
            ELSE 0
		END BASE_ICMS
	, CASE WHEN c.TIPO='NFE' THEN d.ICMS_VALOR
            WHEN c.TIPO='SAT' THEN e.ICMS_VALOR
            WHEN c.TIPO='NFCE' THEN f.ICMS_VALOR
            ELSE 0
		END VALOR_ICMS
	 , d.CFOP CFOP_NFE
     , d.BASE_ICMS BASE_ICMS_NFE
     , d.ICMS_VALOR VALOR_ICMS_NFE
     , e.CFOP CFOP_SAT
     , e.BASE_ICMS BASE_ICMS_SAT
     , e.ICMS_VALOR VALOR_ICMS_SAT
  from vendas a join movimentos_operacoes b on a.operacao_codigo=b.codigo 
				join vendas_itens c on a.tipo=c.tipo and a.loja=c.loja and a.codigo=c.codigo
                left join nfes_itens d on c.item=d.item and c.loja=d.loja and c.codigo=d.nfe and c.tipo='NFE'
                left join sats_itens e on c.item=e.item and c.loja=e.loja and c.codigo=e.sat and c.tipo='SAT'
                left join nfces_itens f on c.item=f.item and c.loja=f.loja and c.codigo=f.NFCE and c.tipo='NFCE'
where a.cadastro between '2024-02-01 00:00:00' and '2024-03-01 00:00:00'
  and a.situacao='NORMAL'
  and a.loja=10
  and b.saida=0
   and a.tipo in ('NFE','NFCE','NF','CUPOM','SAT');
   