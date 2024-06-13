class CDA:
    """
    1.2.643.5.1.13.13.11.1379
    0: Код
    1: Отображаемое название
    """
    LOCALIS = ('LOCALIS', 'Местный статус')
    UROGENITAL = ('UROGENITAL', 'Мочеполовая система')
    DIGESTION = ('DIGESTION', 'Система пищеварения')
    CARDIOVASCULAR = ('CARDIOVASCULAR', 'Система кровообращения')
    RESPIRATORY = ('RESPIRATORY', 'Органы дыхания')
    MUSCULOSKELETAL = ('MUSCULOSKELETAL', 'Опорно-двигательная система')
    SKIN = ('SKIN', 'Кожные покровы')
    NERVOUS = ('NERVOUS', 'Нервная система и органы чувств')
    PSYCH = ('PSYCH', 'Психический статус')
    TRTMPLAN = ('TRTMPLAN', 'План лечения')
    OBSPLAN = ('OBSPLAN', 'План обследования')
    PLANACTIVE = ('PLANACTIVE', 'Планируемые мероприятия')
    MEDINTERVENTIONS = ('MEDINTERVENTIONS', 'Медицинские вмешательства')
    SCORES = ('SCORES', 'Объективизированная оценка состояния пациента')
    PATIENTROUTE = (
        'PATIENTROUTE', 'Сведения о пребывании пациента по отделениям')
    DEPARTINFO = ('DEPARTINFO', 'Сведения о пребывании пациента в отделении')
    RISKFACTORS = ('RISKFACTORS', 'Факторы риска')
    PATOBJ = ('PATOBJ', 'Объективные данные')
    FORM = ('FORM', 'Осмотр врачей-специалистов')
    EXAMINFO = ('EXAMINFO', 'Осмотр врачей-специалистов')
    COMPLNTS = ('COMPLNTS', 'Жалобы')
    STATECUR = ('STATECUR', 'Текущее состояние')
    CONSILIUMDECISION = ('CONSILIUMDECISION', 'Решение консилиума')
    ALL = ('ALL', 'Аллергии и непереносимость')
    COMPLNTS = ('COMPLNTS', 'Жалобы')
    AFTERSUR = (
        'AFTERSUR', 'Сведения о состоянии пациента и назначениях после оперативного вмешательства')
    BEFORESUR = (
        'BEFORESUR', 'Сведения о состоянии пациента и проведенных мероприятиях до оперативного вмешательства')
    DOCINFO = ('DOCINFO', 'Сведения о документе')
    VITALPARAM = ('VITALPARAM', 'Витальные параметры')
    RESINFO = ('RESINFO', 'Заключение')
    STATE = ('STATE', 'Состояние пациента')
    vimisConsultationPurpose = (
        'vimisConsultationPurpose', 'Дополнительные сведения о консультации')
    vimisDispensaryObservation = (
        'vimisDispensaryObservation', 'Информация о диспансерном наблюдении')
    vimisDispensaryObservationCheck = (
        'vimisDispensaryObservationCheck', 'Информации о явках пациента на осмотр')
    vimisMedicalCard = ('vimisMedicalCard',
                        'Данные о медицинских картах пациента')
    SUR = ('SUR', 'Оперативное вмешательство')
    vimisConsultationPurpose = (
        'vimisConsultationPurpose', 'Дополнительные сведения о консультации')
    vimisDispensaryObservation = (
        'vimisDispensaryObservation', 'Информация о диспансерном наблюдении')
    vimisDispensaryObservationCheck = (
        'vimisDispensaryObservationCheck', 'Информации о явках пациента на осмотр')
    vimisMedicalCard = ('vimisMedicalCard',
                        'Данные о медицинских картах пациента')
    DGN = ('DGN', 'Диагнозы')
    SCOPORG = (
        'SCOPORG', 'Цель направления и медицинская организация, куда направлен')
    BENEFITS = ('BENEFITS', 'Льготы')
    WORK = ('WORK', 'Место работы и должность, условия труда')
    ELU = ('ELU', 'Описание и обоснование направления')
    GISTCASE = (
        'GISTCASE', 'Регистрационные данные прижизненного патолого-анатомического исследования')
    GISTCASE_DIAG = ('4017', 'Диагноз заболевания (состояния) по данным направления на прижизненное патолого-анатомическое исследование',
                     'Шифр по МКБ-10')  # TODO: А вот потому что два разных имени у одного кода, а!
    GISTSPECIMENS = ('GISTSPECIMENS', 'Информация об исследованных материалах')
    GISTRESULT = (
        'GISTRESULT', 'Результаты прижизненного патолого-анатомического исследования')
    GISTCASE_RESULT = (
        '4025', 'Результаты прижизненного патолого-анатомического исследования')
    GISTCASE_MICR = ('4021', 'Микроскопическое описание')
    GISTCASE_CONCLUSION = ('4020', 'Морфологическое заключение')
    GISTRESULT_DIAG = (
        '4027', 'Диагноз заболевания (состояния) по результатам прижизненного патолого-анатомического исследования')
    GISTRESULT_DIAG_1 = ('809', 'Шифр по МКБ-10')
    SPECIMENS = ('SPECIMENS', 'Информация об исследованных материалах')
    ANALYSERS = (
        'ANALYSERS', 'Информация об использованном оборудовании и расходных материалах')
    RESINSTR = ('RESINSTR', "Результаты инструментальных исследований")
    RESLAB = ('RESLAB', 'Результаты лабораторных исследований')
    PATOLOGY = ('808', u'Выявленные патологии')
    CONCILIUM = ('vimisConciliumMembers', 'vimis1')
    CONCILIUM_PROTOCOL = ('vimisConsiliumProtocol', 'vimis1')
    HOSP = ('HOSP', 'Пребывание в стационаре')
    DEADPATINFO = ('DEADPATINFO', 'Информация  об умершем')
    ABOUTDEAD = ('ABOUTDEAD', 'Информация о причинах смерти')
    DRUG = ('DRUG', 'Назначенные препараты')
    vimisInformation = ('vimisInformation', 'vimis1')
    SERVICES = ('SERVICES', 'Оказанные услуги')
    STATEADM = ('STATEADM', 'Состояние при поступлении')
    STATEDIS = ('STATEDIS', 'Состояние при выписке')
    PROC = ('PROC', 'Исследования и процедуры')
    PLANSUR = ('PLANSUR', 'Планируемое оперативное вмешательство')
    RESMOR = ('RESMOR', 'Результаты морфологических исследований')
    RESCONS = ('RESCONS', 'Консультации врачей специалистов')
    SUM = ('SUM', 'Информация о лечении')
    NONDRUG = ('NONDRUG', 'Немедикаментозное лечение')
    REGIMI = ('REGIMI', 'Режим и рекомендации')
    RECDIET = ('RECDIET', 'Режим и диета')
    RECTREAT = ('RECTREAT', 'Рекомендованное лечение')
    RECWORK = ('RECWORK', 'Трудовые рекомендации')
    RECOTHER = ('RECOTHER', 'Прочие рекомендации')
    TRANSFUSINFO = ('TRANSFUSINFO', 'Сведения о трансфузии')
    TRANSFUSANAMN = ('TRANSFUSANAMN', 'Трансфузионный анамнез')
    TRANSFUSRSRCH = (
        'TRANSFUSRSRCH', 'Контрольные исследования перед трансфузией')
    MOTHINFO = ('MOTHINFO', 'Информация о матери')
    LABODELI = ('LABODELI', 'Беременность и роды')
    ORGINFO = ('ORGINFO', 'Сведения о медицинской организации')
    MEDEXAMINFO = (
        'MEDEXAMINFO', 'Сведения о диспансеризации или профилактическом медицинском осмотре')
    NBINFO = ('NBINFO', 'Информация о новорождённом')
    AMBS = ('AMBS', 'Сведения амбулаторно-поликлинического обращения')
    ANAM = ('ANAM', 'Анамнез заболевания')
    LANAM = ('LANAM', 'Анамнез жизни')
    REGIME = ('REGIME', 'Режим и рекомендации')
    CATINFO = (
        'CATINFO', 'Категории и подкатегории ТС, на которые предоставляется право управления ТС')
    AMBULANCE = ('AMBULANCE', 'Скорая медицинская помощь')
    NOTES = ('NOTES', 'Примечания')
    PATINFO = ('PATINFO', 'Информация о пациенте')
    HIGHTECHMEDCARE = ('HIGHTECHMEDCARE',
                       'Высокотехнологичная медицинская помощь')
    LINKDOCS = ('LINKDOCS', 'Секции CDA документов')
    LINKDOCS2 = ('LINKDOCS', 'Связанные документы')
    IMM = ('IMM', 'Иммунизация')
    RECIPE = ('RECIPE', 'Рецепт')
    CONSENT = ('CONSENT', 'Сведения о согласии')
    COMMISSION = ('COMMISSION', 'Решение врачебной комиссии')
