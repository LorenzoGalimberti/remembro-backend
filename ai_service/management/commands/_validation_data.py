"""
Nuovo file: remembro-backend/ai_service/management/commands/_validation_data.py

Dati di prova per la validazione manuale della qualità degli agenti AI
(Fase 15, punto 4). Non è un test automatico: serve a produrre output da
leggere a occhio. Il prefisso _ evita che Django lo interpreti come un
comando eseguibile.

NOTIONS: nozioni grezze per GenerationAgent. Il campo "atteso" non viene
usato dal codice, è un promemoria di cosa dovremmo vedere quando
leggiamo il report.

EVALUATION_CASES: casi a domanda/key_points fissi per EvaluationAgent,
con verdetto atteso deciso da noi. Fissi (non generati al volo) così il
risultato è confrontabile tra un giro e l'altro, anche dopo modifiche ai
prompt.
"""

NOTIONS = [
    # --- fatti atomici: dovrebbero produrre 1 sola card, niente sintesi ---
    {
        "category": "Storia",
        "content": "La Rivoluzione francese inizia il 14 luglio 1789 con la presa della Bastiglia.",
        "atteso": "1 card atomica (data/evento), nessuna sintesi",
    },
    {
        "category": "Chimica",
        "content": "Il simbolo chimico dell'oro è Au, dal latino aurum.",
        "atteso": "1 card atomica, possibile cloze",
    },
    {
        "category": "Geografia",
        "content": "Il fiume più lungo d'Italia è il Po, con 652 km.",
        "atteso": "1 card atomica con il numero nei key_points",
    },
    {
        "category": "Informatica",
        "content": "In Python, una lista è mutabile mentre una tupla è immutabile.",
        "atteso": "1-2 card, contrasto tra i due concetti",
    },
    # --- concetti complessi: dovrebbero atomizzare + generare sintesi ---
    {
        "category": "Biologia",
        "content": (
            "La fotosintesi clorofilliana avviene nei cloroplasti delle cellule vegetali. "
            "Nella fase luminosa, l'energia solare viene catturata dalla clorofilla e usata "
            "per scindere l'acqua, liberando ossigeno e producendo ATP e NADPH. Nella fase "
            "oscura, o ciclo di Calvin, l'ATP e il NADPH prodotti servono a fissare l'anidride "
            "carbonica in glucosio."
        ),
        "atteso": "3-5 atomiche (sede, fase luminosa, fase oscura, prodotti) + 1 sintesi",
    },
    {
        "category": "Economia",
        "content": (
            "L'inflazione è l'aumento generalizzato e prolungato dei prezzi. Le banche centrali "
            "la contrastano alzando i tassi di interesse, che rendono il credito più caro, "
            "riducono i consumi e gli investimenti e quindi raffreddano la domanda. Il rischio "
            "è che tassi troppo alti provochino una recessione."
        ),
        "atteso": "3-4 atomiche (definizione, meccanismo, rischio) + sintesi sul trade-off",
    },
    {
        "category": "Storia",
        "content": (
            "Il Congresso di Vienna del 1815 ridisegnò l'Europa dopo la sconfitta di Napoleone. "
            "Si basò su tre principi: legittimità, ovvero il ritorno delle dinastie deposte; "
            "equilibrio, per impedire che una potenza dominasse le altre; e restaurazione "
            "dell'ordine pre-rivoluzionario. Le decisioni furono prese dalle grandi potenze: "
            "Austria, Russia, Prussia e Regno Unito."
        ),
        "atteso": "4-5 atomiche (i tre principi + le potenze) + sintesi",
    },
    {
        "category": "Informatica",
        "content": (
            "Il protocollo HTTPS cifra il traffico tra client e server usando TLS. Il server "
            "presenta un certificato firmato da una Certificate Authority, che il client "
            "verifica per confermare l'identità del server. Dopo la verifica avviene lo "
            "scambio di chiavi, che stabilisce una chiave simmetrica usata per cifrare la "
            "sessione, più veloce della crittografia asimmetrica."
        ),
        "atteso": "4-5 atomiche + sintesi sul perché il misto asimmetrico/simmetrico",
    },
    {
        "category": "Medicina",
        "content": (
            "Gli antibiotici agiscono solo sui batteri, non sui virus. L'uso eccessivo o "
            "interrotto prima del termine favorisce la selezione di ceppi resistenti: i "
            "batteri sensibili muoiono, quelli con mutazioni casuali resistenti sopravvivono "
            "e si moltiplicano. Per questo è importante completare sempre il ciclo prescritto."
        ),
        "atteso": "3-4 atomiche + sintesi sul meccanismo evolutivo",
    },
    {
        "category": "Filosofia",
        "content": (
            "Per Kant la conoscenza nasce dall'incontro tra sensibilità e intelletto: i sensi "
            "forniscono il materiale grezzo, l'intelletto lo organizza attraverso categorie a "
            "priori come causa ed effetto. Ne consegue che conosciamo i fenomeni, ovvero le "
            "cose come ci appaiono, ma non i noumeni, le cose in sé."
        ),
        "atteso": "3-4 atomiche + sintesi; test su contenuto astratto",
    },
    # --- casi limite / stress ---
    {
        "category": "Finanza",
        "content": (
            "L'interesse composto fa crescere il capitale in modo esponenziale perché gli "
            "interessi maturati vengono reinvestiti e producono a loro volta interessi. "
            "Con la regola del 72, si stima il tempo di raddoppio dividendo 72 per il tasso "
            "percentuale annuo: al 6% servono circa 12 anni."
        ),
        "atteso": "concetto + formula numerica; verificare che i numeri finiscano nei key_points",
    },
    {
        "category": "Diritto",
        "content": (
            "L'articolo 21 della Costituzione italiana tutela la libertà di manifestazione del "
            "pensiero con ogni mezzo di diffusione. Non è però illimitata: incontra il limite "
            "del buon costume, ed è bilanciata con altri diritti come l'onore e la reputazione, "
            "tutelati dalle norme sulla diffamazione."
        ),
        "atteso": "atomiche su norma + limiti; verificare precisione del riferimento normativo",
    },
    {
        "category": "Fisica",
        "content": "L'accelerazione di gravità terrestre vale circa 9,81 m/s².",
        "atteso": "1 card atomica, valore numerico preservato con unità di misura",
    },
    {
        "category": "Psicologia",
        "content": (
            "La curva dell'oblio di Ebbinghaus mostra che dimentichiamo rapidamente ciò che "
            "abbiamo appena appreso: entro 24 ore si può perdere fino al 70% delle informazioni. "
            "Il ripasso distanziato contrasta questo declino: ogni ripetizione appiattisce la "
            "curva e allunga il tempo di ritenzione."
        ),
        "atteso": "atomiche + sintesi; meta-test, è il principio alla base dell'app stessa",
    },
    {
        "category": "Arte",
        "content": (
            "La prospettiva lineare viene formalizzata a Firenze nel Quattrocento da "
            "Brunelleschi e teorizzata da Leon Battista Alberti nel De pictura. Si basa su un "
            "punto di fuga verso cui convergono le linee ortogonali, creando l'illusione della "
            "profondità su una superficie piana."
        ),
        "atteso": "atomiche su chi/quando/come + sintesi",
    },
    {
        "category": "Linguistica",
        "content": (
            "Il congiuntivo in italiano esprime soggettività, dubbio o irrealtà, in opposizione "
            "all'indicativo che esprime fatti certi. Si usa nelle subordinate rette da verbi di "
            "opinione, volontà o timore, come credere, volere, temere."
        ),
        "atteso": "atomiche su funzione e contesti d'uso",
    },
    {
        "category": "Biologia",
        "content": "Il DNA è composto da quattro basi azotate: adenina, timina, citosina e guanina.",
        "atteso": "1 card, lista di 4 elementi nei key_points (attenzione al limite di 5)",
    },
    {
        "category": "Storia",
        "content": (
            "La caduta dell'Impero romano d'Occidente è convenzionalmente datata al 476 d.C., "
            "con la deposizione di Romolo Augustolo da parte di Odoacre. Le cause furono "
            "molteplici: crisi economica, pressione delle popolazioni germaniche ai confini, "
            "instabilità politica interna e progressiva difficoltà a difendere un territorio "
            "troppo esteso."
        ),
        "atteso": "atomiche su data/evento + cause multiple, sintesi sulla multifattorialità",
    },
    # --- testi problematici: vaghi o mal formati ---
    {
        "category": "Generale",
        "content": "Ricordarsi di studiare meglio il capitolo sulle equazioni differenziali.",
        "atteso": "CASO LIMITE: non è una nozione, è un promemoria. Cosa fa l'agente?",
    },
    {
        "category": "Generale",
        "content": (
            "appunti lezione: mitocondri = centrali energetiche, ATP, membrana doppia, "
            "DNA proprio (teoria endosimbiotica!!) -- rivedere"
        ),
        "atteso": "CASO LIMITE: appunti sgrammaticati con abbreviazioni, regge?",
    },
]


EVALUATION_CASES = [
    # --- risposte pienamente corrette ---
    {
        "question": "Che cos'è la fotosintesi clorofilliana e dove avviene?",
        "key_points": [
            "processo che converte energia luminosa in energia chimica",
            "avviene nei cloroplasti",
            "produce glucosio e ossigeno",
        ],
        "answer": (
            "È il processo con cui le piante usano la luce del sole per produrre glucosio "
            "e ossigeno, e avviene nei cloroplasti."
        ),
        "atteso": "correct",
    },
    {
        "question": "Perché le banche centrali alzano i tassi per contrastare l'inflazione?",
        "key_points": [
            "tassi più alti rendono il credito più caro",
            "si riducono consumi e investimenti",
            "la domanda si raffredda e i prezzi rallentano",
        ],
        "answer": (
            "Perché se il denaro costa di più la gente e le imprese prendono meno prestiti, "
            "quindi si spende e si investe meno, la domanda cala e i prezzi smettono di salire."
        ),
        "atteso": "correct",
    },
    {
        "question": "In che anno è caduto l'Impero romano d'Occidente?",
        "key_points": ["476 d.C.", "deposizione di Romolo Augustolo"],
        "answer": "Nel 476 dopo Cristo, quando Odoacre depose Romolo Augustolo.",
        "atteso": "correct",
    },
    # --- corrette nel nucleo ma senza dettagli secondari (il tuning del prompt) ---
    {
        "question": "Perché l'uso scorretto degli antibiotici favorisce la resistenza batterica?",
        "key_points": [
            "gli antibiotici uccidono i batteri sensibili",
            "i batteri con mutazioni resistenti sopravvivono",
            "i sopravvissuti si moltiplicano e diventano dominanti",
            "interrompere il ciclo lascia in vita i più resistenti",
        ],
        "answer": (
            "Perché sopravvivono solo i batteri resistenti, che poi si riproducono e "
            "diventano la maggioranza."
        ),
        "atteso": "correct (nucleo colto, mancano dettagli secondari — verifica del tuning)",
    },
    {
        "question": "Qual è la differenza tra fenomeno e noumeno in Kant?",
        "key_points": [
            "il fenomeno è la cosa come ci appare",
            "il noumeno è la cosa in sé",
            "possiamo conoscere solo i fenomeni",
            "le categorie a priori organizzano l'esperienza",
        ],
        "answer": "Il fenomeno è come le cose ci appaiono, il noumeno è la cosa in sé che non possiamo conoscere.",
        "atteso": "correct (manca il punto sulle categorie, ma il nucleo è esatto)",
    },
    # --- parziali veri: nucleo incompleto o confuso ---
    {
        "question": "Che cos'è la fotosintesi clorofilliana e dove avviene?",
        "key_points": [
            "processo che converte energia luminosa in energia chimica",
            "avviene nei cloroplasti",
            "produce glucosio e ossigeno",
        ],
        "answer": "È quando le piante respirano e producono ossigeno.",
        "atteso": "partial (ossigeno giusto, ma confonde con la respirazione)",
    },
    {
        "question": "Su cosa si basa la prospettiva lineare?",
        "key_points": [
            "punto di fuga",
            "linee ortogonali che convergono",
            "illusione di profondità su superficie piana",
        ],
        "answer": "Serve a far sembrare i quadri tridimensionali.",
        "atteso": "partial (effetto giusto, meccanismo assente)",
    },
    {
        "question": "Quali sono i tre principi del Congresso di Vienna?",
        "key_points": ["legittimità", "equilibrio", "restaurazione"],
        "answer": "Legittimità ed equilibrio tra le potenze.",
        "atteso": "partial (2 su 3 in una domanda che chiede esplicitamente tutti e tre)",
    },
    # --- sbagliate ---
    {
        "question": "In che anno è caduto l'Impero romano d'Occidente?",
        "key_points": ["476 d.C.", "deposizione di Romolo Augustolo"],
        "answer": "Nel 1453, con la caduta di Costantinopoli.",
        "atteso": "incorrect (è l'Impero d'Oriente)",
    },
    {
        "question": "Gli antibiotici sono efficaci contro i virus?",
        "key_points": ["no, agiscono solo sui batteri", "i virus richiedono antivirali"],
        "answer": "Sì, servono per curare l'influenza e il raffreddore.",
        "atteso": "incorrect",
    },
    {
        "question": "Che cos'è l'interesse composto?",
        "key_points": [
            "gli interessi maturati vengono reinvestiti",
            "producono a loro volta interessi",
            "la crescita è esponenziale",
        ],
        "answer": "È l'interesse che la banca applica sui mutui quando sei in ritardo con le rate.",
        "atteso": "incorrect",
    },
    # --- casi ostili: risposte evasive o furbe ---
    {
        "question": "Perché il TLS usa sia crittografia asimmetrica sia simmetrica?",
        "key_points": [
            "l'asimmetrica serve a scambiare la chiave in sicurezza",
            "la simmetrica è più veloce",
            "la sessione viene cifrata con chiave simmetrica",
        ],
        "answer": "Per motivi di sicurezza e di prestazioni.",
        "atteso": "partial (formalmente vero ma vuoto: verifica che non premi risposte generiche)",
    },
    {
        "question": "Che cos'è la curva dell'oblio di Ebbinghaus?",
        "key_points": [
            "mostra il decadimento rapido della memoria nel tempo",
            "fino al 70% perso entro 24 ore",
            "il ripasso distanziato appiattisce la curva",
        ],
        "answer": "Non me lo ricordo bene, ma ha a che fare con la memoria e con il dimenticare.",
        "atteso": "incorrect o partial (ammette di non sapere: verifica che non sia generoso)",
    },
]
