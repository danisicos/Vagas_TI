import itertools

# Papéis/cargos que aparecem combinados com uma área de TI nos editais
PREFIXOS = [
    'administrador', 'analista', 'análise', 'arquiteto', 'assistente', 'auditor',
    'auxiliar', 'chefe', 'cientista', 'consultor', 'coordenador', 'desenvolvedor',
    'desenvolvimento', 'diretor', 'engenheiro', 'engenharia', 'especialista',
    'gestão', 'gestor', 'infraestrutura', 'instrutor', 'manutenção', 'monitor',
    'operador', 'perito', 'processamento', 'profissional', 'professor',
    'programação', 'programador', 'supervisor', 'suporte', 'técnico', 'tecnólogo',
]

# Conectores mais comuns entre papel e área nos editais
CONECTORES = ['de', 'em']

# Áreas/domínios de TI - também usados sozinhos, sem papel na frente.
AREAS_TI = [
    'informática', 'tecnologia', 'tecnologia da informação', 'ti', 't.i.',
    'sistemas', 'sistemas de informação', 'sistemas computacionais',
    'redes', 'infraestrutura', 'banco de dados', 'dados', 'big data',
    'segurança da informação', 'segurança cibernética', 'segurança de software',
    'cibersegurança', 'cybersegurança', 'inteligência artificial',
    'machine learning', 'ia', 'geoprocessamento', 'geotecnologia', 'gis',
    'telecomunicações', 'hardware', 'software', 'computação',
    'ciência da computação', 'ciências da computação', 'forense digital',
    'computação forense', 'governança de ti', 'computador', 'computadores',
    'suporte', 'testes', 'help desk', 'soluções', 'aplicações',
    'automação', 'desenvolvimento de software', 'desenvolvimento de sistemas',
]

# Áreas seguras para aparecerem sozinhas 
AREAS_BARE = [
    'tecnologia da informação', 'sistemas de informação', 'sistema de informação',
    'sistemas da informação', 'sistema da informação', 'sistemas computacionais',
    'banco de dados', 'segurança da informação', 'segurança cibernética',
    'segurança de software', 'cibersegurança', 'cybersegurança',
    'inteligência artificial', 'machine learning', 'ciência da computação',
    'ciências da computação', 'forense digital', 'computação forense',
    'governança de ti', 'redes de computadores', 'rede de computadores',
    'sistemas de software', 'help desk', 'big data',
]

# Termos irregulares que não seguem o padrão "papel + conector + área"
EXTRAS = [
    'programador',
    'digitalizador',
    'desenvolvedor de programas',
    'analista forense digital',
    'analista de desenvolvimento de sistemas',
    'análise e desenvolvimento de sistemas',
    'assistente em ciência e tecnologia',
    'desenvolvedor frontend',
    'desenvolvedor fullstack',
    'desenvolvedor backend',
    'desenvolvedor web',
    'engenheiro da computação',
    'engenharia da computação',
    'gestão da tecnologia da informação',
    'tecnologia de ti',
    'tecnologia de t.i.',
    'tecnologia em ti',
    'tecnologia em t.i.',
    'tecnólogo da informação',
    'tecnólogo em gestão da tecnologia da informação',
    'tecnólogo em sistemas para internet',
    'rede de computadores',
    'redes de computadores',
    'sistema da informação',
    'sistema de informação',
    'sistemas da informação',
    'sistemas de software',
    'matemática computacional',
    'matemática da computação',
]

_COMBINACOES = (
    f'{prefixo} {conector} {area}'
    for prefixo, conector, area in itertools.product(PREFIXOS, CONECTORES, AREAS_TI)
)

# Lista final: áreas seguras soltas + termos irregulares + combinações papel+conector+área, sem duplicatas
CARGOS = list(dict.fromkeys([*AREAS_BARE, *EXTRAS, *_COMBINACOES]))
