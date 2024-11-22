"""
Test suite for core functionality of Allegro IO Code Assistant.
"""

from src.core.session import SessionManager
from src.core.llm import LLMManager
from src.core.files import FileManager

# Setup per i test che usano st.session_state
@pytest.fixture(autouse=True)
def setup_streamlit():
    if 'session_state' not in dir(st):
        st.session_state = {}

class TestSessionManager:
    """Test per SessionManager."""
    
    def test_init_session(self):
        """Test inizializzazione sessione."""
        SessionManager.init_session()
        assert st.session_state.initialized == True
        assert isinstance(st.session_state.chat_history, list)
        assert st.session_state.current_model == 'o1-mini'
        assert isinstance(st.session_state.files, dict)
    
    def test_chat_history_management(self):
        """Test gestione chat history."""
        SessionManager.init_session()
        test_message = {"role": "user", "content": "test"}
        
        SessionManager.add_to_chat_history(test_message)
        history = SessionManager.get_chat_history()
        
        assert len(history) == 1
        assert history[0] == test_message
        
        SessionManager.clear_chat_history()
        assert len(SessionManager.get_chat_history()) == 0
    
    def test_file_management(self):
        """Test gestione file."""
        SessionManager.init_session()
        test_file = ("content", "python", 100)
        
        SessionManager.add_file("test.py", test_file)
        assert SessionManager.get_file("test.py") == test_file
        
        SessionManager.set_current_file("test.py")
        assert SessionManager.get_current_file() == "test.py"
    
    def test_stats_tracking(self):
        """Test tracking statistiche."""
        SessionManager.init_session()
        
        SessionManager.update_token_count(100)
        SessionManager.update_cost(0.002)
        
        stats = SessionManager.get_stats()
        assert stats['token_count'] == 100
        assert stats['cost'] == 0.002

class TestLLMManager:
    """Test per LLMManager."""
    
    @pytest.fixture
    def llm_manager(self):
        """Fixture per LLMManager."""
        with patch('openai.OpenAI'), patch('anthropic.Anthropic'):
            return LLMManager()
    
    def test_model_selection(self, llm_manager):
        """Test selezione modello."""
        # Test per file grandi
        assert llm_manager.select_model("debug", 150_000) == "claude-3-5-sonnet"
        
        # Test per review
        assert llm_manager.select_model("review", 1000) == "o1-preview"
        
        # Test per task semplici
        assert llm_manager.select_model("debug", 1000) == "o1-mini"
    
    def test_template_loading(self, llm_manager):
        """Test caricamento template."""
        with patch('builtins.open', mock_open(read_data="Test {prompt}")):
            template = llm_manager.get_template("test")
            assert template == "Test {prompt}"
    
    @pytest.mark.asyncio
    async def test_process_request(self, llm_manager):
        """Test processing richieste."""
        test_response = "Test response"
        with patch.object(llm_manager, '_call_openai', return_value=iter([test_response])):
            response = []
            async for chunk in llm_manager.process_request("test prompt"):
                response.append(chunk)
            assert "".join(response) == test_response

class TestFileManager:
    """Test per FileManager."""
    
    @pytest.fixture
    def file_manager(self):
        """Fixture per FileManager."""
        return FileManager()
    
    def test_file_processing(self, file_manager):
        """Test processing file."""
        mock_file = MagicMock()
        mock_file.name = "test.py"
        mock_file.read.return_value = b"print('test')"
        
        content, lang, size = file_manager.process_file(mock_file)
        assert content == "print('test')"
        assert lang == "python"
        assert size == 12
    
    def test_zip_processing(self, file_manager):
        """Test processing file ZIP."""
        import io
        import zipfile
        
        # Crea un file ZIP di test
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr('test.py', "print('test')")
        
        mock_zip = MagicMock()
        mock_zip.read.return_value = zip_buffer.getvalue()
        
        files = file_manager.process_zip(mock_zip)
        assert 'test.py' in files
        assert files['test.py'][0] == "print('test')"
    
    def test_file_tree_creation(self, file_manager):
        """Test creazione file tree."""
        files = {
            'folder/test.py': ('content', 'python', 100),
            'folder/sub/other.py': ('content', 'python', 100)
        }
        
        tree = file_manager.create_file_tree(files)
        assert 'folder' in tree
        assert 'test.py' in tree['folder']
        assert 'sub' in tree['folder']
        assert 'other.py' in tree['folder']['sub']
    
    def test_syntax_highlighting(self, file_manager):
        """Test syntax highlighting."""
        code = "print('test')"
        highlighted = file_manager.highlight_code(code, "python")
        assert 'class="source"' in highlighted
        assert 'print' in highlighted