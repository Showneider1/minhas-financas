"""
KALDROX/TIBIA 8.60 - LOGIN AUTOMÁTICO
Versão final com compatibilidade de input libraries
"""

import time
from pymem import Pymem
import win32gui
import win32con
import psutil

# Tenta importar biblioteca de input (prioridade: pyautogui > pydirectinput)
try:
    import pyautogui as input_lib
    INPUT_LIB = "pyautogui"
    print("✓ Usando pyautogui para input")
except ImportError:
    try:
        import pydirectinput as input_lib
        INPUT_LIB = "pydirectinput"
        print("✓ Usando pydirectinput para input")
    except ImportError:
        print("✗ ERRO: Instale pyautogui ou pydirectinput")
        print("   pip install pyautogui")
        exit(1)


class KaldroxLogin:
    """Login para Kaldrox Client e Tibia 8.60"""

    # Endereços de validação (Player info)
    PLAYER_ID = 0x63FE98
    PLAYER_HEALTH = 0x63FE94
    PLAYER_MAX_HEALTH = 0x63FE90
    PLAYER_LEVEL = 0x63FE88
    PLAYER_NAME = 0x63FE6C
    PLAYER_MANA = 0x63FE9C
    PLAYER_MAX_MANA = 0x63FEA0

    def __init__(self, account: str, password: str, char_index: int = 0):
        self.account = account
        self.password = password
        self.char_index = char_index
        self.pm = None
        self.hwnd = None
        self.process_name = None

    def find_client_process(self) -> bool:
        """Encontra o processo do cliente automaticamente"""
        print("🔍 Procurando cliente Tibia/Kaldrox...\n")

        keywords = ['tibia', 'kaldrox', 'otclient', 'client']
        found_processes = []

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name']
                proc_name_lower = proc_name.lower()

                if any(keyword in proc_name_lower for keyword in keywords):
                    found_processes.append({
                        'name': proc_name,
                        'pid': proc.info['pid']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if not found_processes:
            print("✗ Nenhum processo encontrado")
            print("\n💡 Processos procurados: tibia, kaldrox, otclient, client")
            return False

        print("✓ Processo(s) encontrado(s):\n")
        for i, proc in enumerate(found_processes, 1):
            print(f"  [{i}] {proc['name']} (PID: {proc['pid']})")

        self.process_name = found_processes[0]['name']
        print(f"\n✓ Usando: {self.process_name}")
        return True

    def connect(self) -> bool:
        """Conecta ao processo do cliente"""
        try:
            if not self.process_name:
                if not self.find_client_process():
                    return False

            print(f"\n🔗 Conectando ao processo: {self.process_name}")
            self.pm = Pymem(self.process_name)
            print(f"✓ Conectado (PID: {self.pm.process_id})")

            self._find_window()
            return True

        except Exception as e:
            print(f"✗ Erro ao conectar: {e}")
            print("\n💡 Tente executar como Administrador")
            return False

    def _find_window(self):
        """Encontra handle da janela do cliente"""
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                keywords = ['tibia', 'kaldrox', 'otclient']
                if any(word in title.lower() for word in keywords):
                    windows.append(hwnd)
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        if windows:
            self.hwnd = windows[0]
            title = win32gui.GetWindowText(self.hwnd)
            print(f"✓ Janela encontrada: '{title}'")
        else:
            print("⚠ Janela não encontrada (continuando sem foco)")

    def focus_window(self):
        """Foca janela do cliente"""
        if self.hwnd:
            try:
                if win32gui.IsIconic(self.hwnd):
                    win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                    time.sleep(0.2)

                win32gui.SetForegroundWindow(self.hwnd)
                time.sleep(0.3)
            except Exception as e:
                print(f"⚠ Aviso ao focar janela: {e}")

    def press_hotkey(self, *keys):
        """Pressiona combinação de teclas (compatível com ambas as libs)"""
        if INPUT_LIB == "pyautogui":
            # pyautogui tem hotkey nativo
            input_lib.hotkey(*keys)
        else:
            # pydirectinput não tem hotkey, simula manualmente
            # Pressiona todas as teclas
            for key in keys:
                input_lib.keyDown(key)
                time.sleep(0.05)

            # Solta todas as teclas (ordem inversa)
            for key in reversed(keys):
                input_lib.keyUp(key)
                time.sleep(0.05)

    def type_text(self, text: str, interval: float = 0.05):
        """Digite texto caractere por caractere"""
        for char in text:
            input_lib.press(char)
            time.sleep(interval)
        time.sleep(0.2)

    def press_key(self, key: str, times: int = 1, delay: float = 0.2):
        """Pressiona uma tecla"""
        for _ in range(times):
            input_lib.press(key)
            time.sleep(delay)

    def clear_field(self):
        """Limpa campo de texto atual"""
        # Seleciona tudo (CTRL+A)
        self.press_hotkey('ctrl', 'a')
        time.sleep(0.1)

        # Apaga
        self.press_key('backspace', delay=0.1)
        time.sleep(0.1)

    def read_string(self, address: int, length: int = 32) -> str:
        """Lê string da memória"""
        try:
            data = self.pm.read_bytes(address, length)
            null_pos = data.find(b'\x00')
            if null_pos != -1:
                data = data[:null_pos]
            return data.decode('latin-1', errors='ignore')
        except:
            return ""

    def is_in_game(self) -> bool:
        """Verifica se player está no jogo via memória"""
        try:
            player_id = self.pm.read_int(self.PLAYER_ID)
            player_hp = self.pm.read_int(self.PLAYER_HEALTH)
            return player_id > 0 and player_hp > 0
        except:
            return False

    def get_player_info(self) -> dict:
        """Lê informações do player da memória"""
        try:
            return {
                'id': self.pm.read_int(self.PLAYER_ID),
                'name': self.read_string(self.PLAYER_NAME, 32),
                'level': self.pm.read_int(self.PLAYER_LEVEL),
                'hp': self.pm.read_int(self.PLAYER_HEALTH),
                'max_hp': self.pm.read_int(self.PLAYER_MAX_HEALTH),
                'mana': self.pm.read_int(self.PLAYER_MANA),
                'max_mana': self.pm.read_int(self.PLAYER_MAX_MANA)
            }
        except Exception as e:
            return {'error': str(e)}

    def input_credentials(self):
        """Preenche credenciais usando teclado"""
        print("\n📝 PREENCHENDO CREDENCIAIS")
        print("-"*70)

        self.focus_window()
        time.sleep(0.5)

        # Campo Account Name
        print("⌨ Campo Account Name...")
        self.press_key('tab', times=1, delay=0.3)
        self.clear_field()

        print(f"   └─ Digitando: {self.account}")
        self.type_text(self.account, interval=0.05)
        time.sleep(0.2)

        # Campo Password
        print("⌨ Campo Password...")
        self.press_key('tab', times=1, delay=0.3)
        self.clear_field()

        print(f"   └─ Digitando: {'*' * len(self.password)}")
        self.type_text(self.password, interval=0.05)
        time.sleep(0.2)

        print("✓ Credenciais preenchidas")

    def wait_for_game(self, timeout: int = 15) -> bool:
        """Aguarda player entrar no jogo e valida via memória"""
        print(f"\n⏳ Aguardando entrar no jogo ({timeout}s)...")
        print("   └─ Verificando Player ID via memória...")

        start = time.time()
        dots = 0

        while time.time() - start < timeout:
            if self.is_in_game():
                info = self.get_player_info()

                print(f"\n\n✓ PLAYER DETECTADO NO JOGO (via Memory Reading)!")
                print("   " + "="*66)
                print(f"   Nome: {info.get('name', 'N/A')}")
                print(f"   Level: {info.get('level', 0)}")
                print(f"   HP: {info.get('hp', 0)}/{info.get('max_hp', 0)}")
                print(f"   Mana: {info.get('mana', 0)}/{info.get('max_mana', 0)}")
                print(f"   Player ID: {info.get('id', 0)}")
                print("   " + "="*66)

                return True

            elapsed = int(time.time() - start)
            remaining = timeout - elapsed
            dots = (dots + 1) % 4
            print(f"\r   └─ Carregando{'.' * dots}{' ' * (3-dots)} ({remaining}s)   ", 
                  end='', flush=True)
            time.sleep(0.5)

        print(f"\n\n✗ Timeout: Não foi possível detectar entrada no jogo")
        return False

    def run(self) -> bool:
        """Executa sequência completa de login"""
        print("\n" + "="*70)
        print("🤖 KALDROX/TIBIA 8.60 - LOGIN AUTOMÁTICO")
        print("="*70)
        print(f"Account: {self.account}")
        print(f"Password: {'*' * len(self.password)}")
        print(f"Character Index: {self.char_index}")
        print(f"Input Library: {INPUT_LIB}")
        print("="*70)

        try:
            # [1/5] CONECTAR
            print("\n[1/5] CONECTANDO AO PROCESSO")
            print("-"*70)

            if not self.connect():
                return False

            # [2/5] CREDENCIAIS
            print("\n[2/5] PREENCHENDO CREDENCIAIS")
            print("-"*70)

            self.input_credentials()

            # [3/5] LOGIN
            print("\n[3/5] FAZENDO LOGIN")
            print("-"*70)

            print("↵ Pressionando ENTER para LOGIN...")
            self.press_key('enter', delay=0.5)

            print("⏳ Aguardando lista de personagens...")
            time.sleep(3)
            print("✓ Lista carregada (presumido)")

            # [4/5] SELECIONAR CHAR
            print("\n[4/5] SELECIONANDO PERSONAGEM")
            print("-"*70)

            print("⬆ Voltando ao topo da lista...")
            self.press_key('up', times=10, delay=0.1)
            time.sleep(0.3)

            if self.char_index > 0:
                print(f"⬇ Descendo {self.char_index} posição(ões)...")
                self.press_key('down', times=self.char_index, delay=0.2)
                time.sleep(0.3)

            print(f"✓ Personagem {self.char_index} selecionado")

            print("↵ Pressionando ENTER para ENTRAR NO JOGO...")
            self.press_key('enter', delay=0.5)

            # [5/5] VALIDAR
            print("\n[5/5] VALIDANDO ENTRADA NO JOGO")
            print("-"*70)

            if not self.wait_for_game(timeout=15):
                print("\n⚠ Não foi possível confirmar entrada via memória")
                print("  └─ Verifique manualmente se está no jogo")
                return False

            # SUCESSO
            print("\n" + "="*70)
            print("✅ LOGIN COMPLETO COM SUCESSO!")
            print("="*70)
            print("\n🎮 Você está logado e pronto para jogar!")
            print("💡 Próximo: Implemente bot de gameplay com memory reading")

            return True

        except KeyboardInterrupt:
            print("\n\n⚠ Login interrompido pelo usuário (CTRL+C)")
            return False

        except Exception as e:
            print(f"\n\n❌ ERRO INESPERADO: {e}")
            import traceback
            traceback.print_exc()
            return False


# ============================================================================
# CONFIGURAÇÃO E EXECUÇÃO
# ============================================================================

def main():
    """Função principal"""

    # ========================================================================
    # ⚠️ CONFIGURAÇÃO - EDITE AQUI
    # ========================================================================

    ACCOUNT_NAME = "Hunt0001"
    PASSWORD = "Kaldrox1234"
    CHARACTER_INDEX = 1

    # ========================================================================

    if ACCOUNT_NAME == "seu_account" or PASSWORD == "sua_senha":
        print("\n" + "="*70)
        print("⚠️  ATENÇÃO: CONFIGURE SUAS CREDENCIAIS!")
        print("="*70)
        print("\nEdite o arquivo e altere:")
        print("  • ACCOUNT_NAME = 'sua_conta'")
        print("  • PASSWORD = 'sua_senha'")
        print("  • CHARACTER_INDEX = 0")
        print("\n" + "="*70)
        return

    print("\n" + "="*70)
    print("📋 PRÉ-REQUISITOS")
    print("="*70)
    print("✓ Cliente Kaldrox/Tibia 8.60 deve estar ABERTO")
    print("✓ Deve estar na TELA DE LOGIN")
    print("✓ NÃO mexa no mouse/teclado durante a execução")
    print("="*70)

    input("\nPressione ENTER para iniciar o login automático...")

    bot = KaldroxLogin(
        account=ACCOUNT_NAME,
        password=PASSWORD,
        char_index=CHARACTER_INDEX
    )

    success = bot.run()

    if not success:
        print("\n" + "="*70)
        print("❌ LOGIN FALHOU")
        print("="*70)
        print("\n🔧 TROUBLESHOOTING:")
        print("  1. O cliente está aberto?")
        print("  2. Está na tela de login (não dentro do jogo)?")
        print("  3. As credenciais estão corretas?")
        print("  4. Tente executar como Administrador")
        print("  5. Verifique se o servidor está online")
        print("="*70)


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║         KALDROX/TIBIA 8.60 - LOGIN BOT v3.0                          ║
║         Compatível com pyautogui e pydirectinput                     ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    print("📦 Instale UMA das bibliotecas de input:")
    print("   pip install pyautogui    (RECOMENDADO)")
    print("   OU")
    print("   pip install pydirectinput\n")

    print("📦 Outras dependências:")
    print("   pip install pymem psutil pywin32\n")

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Bot encerrado pelo usuário")
    except Exception as e:
        print(f"\n💥 Erro fatal: {e}")
        import traceback
        traceback.print_exc()