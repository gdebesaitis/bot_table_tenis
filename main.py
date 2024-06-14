import os
import sqlite3
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Configuração do banco de dados
def configurar_banco():
    conn = sqlite3.connect('jogos_tenis_de_mesa.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador1 TEXT NOT NULL,
            jogador2 TEXT NOT NULL,
            sets INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS placares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogo_id INTEGER,
            set_num INTEGER,
            placar1 INTEGER,
            placar2 INTEGER,
            saldo_pontos_jogador1 INTEGER,
            saldo_pontos_jogador2 INTEGER,
            FOREIGN KEY (jogo_id) REFERENCES jogos (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ranking (
            jogador TEXT PRIMARY KEY,
            sets_vencidos INTEGER DEFAULT 0,
            saldo_pontos INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

configurar_banco()

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True  # Habilitar PRESENCE INTENT
intents.members = True    # Habilitar SERVER MEMBERS INTENT
bot = commands.Bot(command_prefix='!', intents=intents)

# Inicialização do bot
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}!')
    canal_id = # CODIGO DE CANAL DESEJADO PARA O BOT MANDAR UM "OI" 
    canal = bot.get_channel(canal_id)
    if canal:
        await canal.send(":robot: Estou online! Olá, pessoal!")

# Cadastro de jogos
@bot.command(name='cadastrar')
@commands.is_owner()
async def cadastrar_jogo(ctx):
    await ctx.send(":robot: Digite o nome do Jogador 1:")

    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        jogador1_msg = await bot.wait_for('message', check=check_author, timeout=60.0)
        jogador1 = jogador1_msg.content

        await ctx.send(":robot: Digite o nome do Jogador 2:")
        jogador2_msg = await bot.wait_for('message', check=check_author, timeout=60.0)
        jogador2 = jogador2_msg.content

        await ctx.send(":robot: Digite a quantidade de sets:")
        sets_msg = await bot.wait_for('message', check=check_author, timeout=60.0)
        sets = int(sets_msg.content)

        conn = sqlite3.connect('jogos_tenis_de_mesa.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO jogos (jogador1, jogador2, sets)
            VALUES (?, ?, ?)
        ''', (jogador1, jogador2, sets))
        jogo_id = cursor.lastrowid

        sets_vencidos_jogador1 = 0
        sets_vencidos_jogador2 = 0
        saldo_pontos_jogador1 = 0
        saldo_pontos_jogador2 = 0

        for i in range(1, sets + 1):
            await ctx.send(f":robot: Digite o placar do set {i} no formato pontos1xpontos2 (ex: 11x9):")
            placar_msg = await bot.wait_for('message', check=check_author, timeout=60.0)
            placar = placar_msg.content
            pontos1, pontos2 = map(int, placar.split('x'))

            saldo_pontos1 = pontos1 - pontos2
            saldo_pontos2 = pontos2 - pontos1

            cursor.execute('''
                INSERT INTO placares (jogo_id, set_num, placar1, placar2, saldo_pontos_jogador1, saldo_pontos_jogador2)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (jogo_id, i, pontos1, pontos2, saldo_pontos1, saldo_pontos2))

            if pontos1 > pontos2:
                sets_vencidos_jogador1 += 1
            elif pontos2 > pontos1:
                sets_vencidos_jogador2 += 1

            saldo_pontos_jogador1 += saldo_pontos1
            saldo_pontos_jogador2 += saldo_pontos2

        cursor.execute('''
            INSERT OR IGNORE INTO ranking (jogador) VALUES (?)
        ''', (jogador1,))
        cursor.execute('''
            UPDATE ranking SET sets_vencidos = sets_vencidos + ?, saldo_pontos = saldo_pontos + ? WHERE jogador = ?
        ''', (sets_vencidos_jogador1, saldo_pontos_jogador1, jogador1))

        cursor.execute('''
            INSERT OR IGNORE INTO ranking (jogador) VALUES (?)
        ''', (jogador2,))
        cursor.execute('''
            UPDATE ranking SET sets_vencidos = sets_vencidos + ?, saldo_pontos = saldo_pontos + ? WHERE jogador = ?
        ''', (sets_vencidos_jogador2, saldo_pontos_jogador2, jogador2))

        conn.commit()
        conn.close()

        await ctx.send(":robot: Jogo cadastrado com sucesso!")

    except Exception as e:
        await ctx.send(f"Ocorreu um erro: {e}")

# Mostra os jogos de um jogador
@bot.command(name='mostrar')
async def mostrar_jogos(ctx, *, nome_jogador: str = None):
    if nome_jogador is None:
        await ctx.send(":robot: Por favor, forneça o nome de um jogador para ver os jogos cadastrados.")
        return

    conn = sqlite3.connect('jogos_tenis_de_mesa.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT j.id, j.jogador1, j.jogador2, j.sets
        FROM jogos j
        WHERE LOWER(j.jogador1) = LOWER(?) OR LOWER(j.jogador2) = LOWER(?)
    ''', (nome_jogador, nome_jogador))
    jogos = cursor.fetchall()

    if not jogos:
        await ctx.send(f':robot: Nenhum jogo encontrado para o jogador "{nome_jogador}".')
    else:
        for jogo in jogos:
            jogo_id, jogador1, jogador2, sets = jogo
            detalhes_jogo = f"=== Detalhes do Jogo ===\nJogador 1: {jogador1}\nJogador 2: {jogador2}\nQuantidade de Sets: {sets}\n"

            cursor.execute('''
                SELECT set_num, placar1, placar2, saldo_pontos_jogador1, saldo_pontos_jogador2
                FROM placares
                WHERE jogo_id = ?
                ORDER BY set_num
            ''', (jogo_id,))
            placares = cursor.fetchall()

            for placar in placares:
                set_num, placar1, placar2, saldo_pontos1, saldo_pontos2 = placar
                detalhes_jogo += f"Set {set_num}: {jogador1} {placar1} x {placar2} {jogador2}\n"

            detalhes_jogo += "========================\n"
            await ctx.send(detalhes_jogo)

    conn.close()

# Mostra o ranking
@bot.command(name='ranking')
async def mostrar_ranking(ctx):
    conn = sqlite3.connect('jogos_tenis_de_mesa.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT jogador, sets_vencidos, saldo_pontos
        FROM ranking
        ORDER BY sets_vencidos DESC, saldo_pontos DESC
    ''')
    ranking = cursor.fetchall()

    if not ranking:
        await ctx.send(':robot: Nenhum jogador cadastrado ainda.')
    else:
        mensagem = '====== :ping_pong: :trophy: Ranking de Jogadores :trophy: :ping_pong: ======\n'
        posicao = 1
        for i in range(len(ranking)):
            if i > 0 and (ranking[i][1] != ranking[i-1][1] or ranking[i][2] != ranking[i-1][2]):
                posicao = i + 1
            jogador_nome, sets_vencidos, saldo_pontos = ranking[i]
            mensagem += f'{posicao}. {jogador_nome} - Sets Vencidos: {sets_vencidos}, Saldo de Pontos: {saldo_pontos}\n'

        await ctx.send(mensagem)

    conn.close()

# Desativa o bot
@bot.command(name='sair')
@commands.is_owner()
async def sair(ctx):
    await ctx.send(":robot: Vazando! Até a próxima!")
    await bot.close()

# Bot diz oi
@bot.command(name='oi')
async def oi(ctx):
    await ctx.send(":robot: Olá! Vamos jogar? Digite !comandos para ver os comandos disponíveis.")
    await bot.close()

# Sobre o bot
@bot.command(name='sobre')
async def sobre(ctx):
    await ctx.send(":robot: Meu nome é Ping Pong Bot!\nFui criado pelo @guilherme.dna e estou na versão 1.140624!\nDigite !comandos para ver os comandos disponíveis.")

# Regras
@bot.command(name='regras')
async def regras(ctx):
    await ctx.send(":robot: Aprenda as regras do Tênis de Mesa em: https://www.hobbytt.com.br/blog/regras-basica-do-tenis-de-mesa/ ")

# Lista de comandos
@bot.command(name='comandos')
@commands.is_owner()
async def comandos(ctx):
    #if ctx.channel.id != # INSIRA AQUI O ID DE UM CANAL DE VOZ CASO QUEIRA DEIXAR ESTE COMANDO FUNCIONAL APENAS NO CANAL ESPECIFICADO
        #await ctx.send(":robot: Este comando só pode ser usado no canal permitido.")
        #return

    mensagem = (
        "=================     COMANDOS     ================\n"
        "!cadastrar         -> Cadastre um novo jogo!\n"
        "!mostrar + <nome>  -> Veja os jogos cadastrados!\n"
        "!ranking           -> Veja o ranking dos jogadores!\n"
        "!zerareg           -> Zere o ranking dos jogadores!\n"
        "!regras            -> Veja as Regras do Tênis de Mesa!\n"
        "!oi                -> Auto-explicativo!\n"
        "!sobre             -> Sobre o bot!\n"
        "!campeao           -> Veja o campeão do Tênis de Mesa!\n"
        "!limpar            -> Adicione um número entre 1 e 100 junto com o comando e Limpe o chat!\n"
        "!sair              -> Encerre o bot!\n"
    )
    await ctx.send(f"```{mensagem}```")

# Mostra o primeiro colocado do ranking
@bot.command(name='campeao')
async def campeao(ctx):
    conn = sqlite3.connect('jogos_tenis_de_mesa.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT jogador, sets_vencidos, saldo_pontos
        FROM ranking
        ORDER BY sets_vencidos DESC
        LIMIT 1
    ''')
    campeao = cursor.fetchone()

    if campeao:
        jogador, sets_vencidos, saldo_pontos = campeao
        mensagem = f"🏆 O campeão atual é {jogador} com {sets_vencidos} sets vencidos e saldo {saldo_pontos}."
    else:
        mensagem = ":robot: Não há jogadores cadastrados ainda."

    await ctx.send(mensagem)

    conn.close()

# Limpa chat
@bot.command(name='limpar')
@commands.is_owner()
async def limpar(ctx, quantidade: int):
    if quantidade <= 0 or quantidade > 100:
        await ctx.send(":robot: Por favor, especifique um número entre 1 e 100 para limpar.")
        return

    try:
        await ctx.channel.purge(limit=quantidade)
        await ctx.send(f":broom: Limpei {quantidade} mensagens neste canal. :broom:")
    except Exception as e:
        await ctx.send(f"Ocorreu um erro ao tentar limpar as mensagens: {e}")

# Zera as tabelas
@bot.command(name='zerareg')
@commands.is_owner()
async def drop_tables(ctx):
    if ctx.author.id != # INSIRA AQUI O ID DO USUARIO QUE PODE USAR ESTE COMANDO 
        await ctx.send(":robot: Este comando só pode ser usado pelo administrador!")
        return
        
    await ctx.send(":robot: Para confirmar a exclusão das tabelas, digite a senha: ")

    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel

    senha_msg = await bot.wait_for('message', check=check_author, timeout=60.0)
    senha = senha_msg.content

    if senha == "1234":
        conn = sqlite3.connect('jogos_tenis_de_mesa.db')
        cursor = conn.cursor()
        cursor.execute('''DROP TABLE IF EXISTS placares''')
        cursor.execute('''DROP TABLE IF EXISTS jogos''')
        cursor.execute('''DROP TABLE IF EXISTS ranking''')
        conn.commit()
        conn.close()
        await ctx.send(":robot: Tabelas excluídas com sucesso.")
        configurar_banco()
        await ctx.send(":robot: Tabelas recriadas com sucesso.")
    else:
        await ctx.send(":robot: Senha incorreta. Operação cancelada.")

# Iniciar o bot
bot.run(' # AQUI VAI O TOKEN DO SEU SERVIDOR ' )
