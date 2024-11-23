"""
UI components for Allegro IO Code Assistant.
Streamlit-based interface components for file exploration,
chat interface, code viewing, and stats display.
"""

import streamlit as st
from typing import Dict, Any, Optional
import os
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter
import time

class FileExplorer:
    """A simplified file explorer component for Streamlit."""
    
    ALLOWED_EXTENSIONS = {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css',
        '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php',
        '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh',
        '.sql', '.md', '.txt', '.json', '.yml', '.yaml'
    }
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    def __init__(self):
        """Initialize the FileExplorer component."""
        if 'files' not in st.session_state:
            st.session_state.files = {}
        if 'selected_file' not in st.session_state:
            st.session_state.selected_file = None
    
    def _process_file_content(self, content: str, filename: str) -> Dict[str, Any]:
        """Process and format file content."""
        try:
            lexer = get_lexer_for_filename(filename)
            language = lexer.name.lower()
        except:
            language = 'text'
            lexer = TextLexer()
            
        formatter = HtmlFormatter(
            style='monokai',
            linenos=True,
            cssclass='source'
        )
        
        highlighted = highlight(content, lexer, formatter)
        
        return {
            'content': content,
            'language': language,
            'name': filename,
            'highlighted': highlighted,
            'size': len(content)
        }
    
    def _get_file_icon(self, filename: str) -> str:
        """Get appropriate icon for file type."""
        ext = os.path.splitext(filename)[1].lower()
        icons = {
            '.py': '🐍',
            '.js': '📜',
            '.jsx': '⚛️',
            '.ts': '📘',
            '.tsx': '💠',
            '.html': '🌐',
            '.css': '🎨',
            '.md': '📝',
            '.txt': '📄',
            '.json': '📋',
            '.yml': '⚙️',
            '.yaml': '⚙️',
            '.zip': '📦'
        }
        return icons.get(ext, '📄')
    
    def render(self):
        """Render the file explorer component."""
        uploaded_files = st.file_uploader(
            "Upload Files",
            type=[ext[1:] for ext in self.ALLOWED_EXTENSIONS],
            accept_multiple_files=True,
            key="file_uploader"
        )

        if uploaded_files:
            for file in uploaded_files:
                try:
                    if file.name.endswith('.zip'):
                        with ZipFile(BytesIO(file.read()), 'r') as zip_ref:
                            for zip_file in zip_ref.namelist():
                                if (not zip_file.startswith('__') and 
                                    not zip_file.startswith('.') and 
                                    not zip_file.endswith('/')):
                                    try:
                                        content = zip_ref.read(zip_file).decode('utf-8', errors='ignore')
                                        if len(content) <= self.MAX_FILE_SIZE:
                                            processed_file = self._process_file_content(content, zip_file)
                                            st.session_state.files[zip_file] = processed_file
                                    except Exception as e:
                                        st.warning(f"Error processing {zip_file}: {str(e)}")
                    else:
                        content = file.read().decode('utf-8')
                        if len(content) <= self.MAX_FILE_SIZE:
                            processed_file = self._process_file_content(content, file.name)
                            st.session_state.files[file.name] = processed_file
                except Exception as e:
                    st.error(f"Error processing {file.name}: {str(e)}")

        # Display uploaded files
        if st.session_state.files:
            st.markdown("### 📁 Files")
            # Create columns for file list and actions
            for filename, file_info in st.session_state.files.items():
                col1, col2 = st.columns([4, 1])
                with col1:
                    icon = self._get_file_icon(filename)
                    if st.button(
                        f"{icon} {filename}",
                        key=f"file_{filename}",
                        use_container_width=True,
                        type="secondary" if st.session_state.selected_file != filename else "primary"
                    ):
                        st.session_state.selected_file = filename
                with col2:
                    if st.button("🗑️", key=f"delete_{filename}"):
                        del st.session_state.files[filename]
                        if st.session_state.selected_file == filename:
                            st.session_state.selected_file = None
                        st.rerun()

class ChatInterface:
    """Chat interface component."""
    
    def __init__(self):
        """Initialize chat interface."""
        if 'chats' not in st.session_state:
            st.session_state.chats = {
                'Chat principale': {
                    'messages': [{
                        "role": "assistant",
                        "content": "Ciao! Carica dei file e fammi delle domande su di essi."
                    }],
                    'created_at': datetime.now().isoformat()
                }
            }
            st.session_state.current_chat = 'Chat principale'
    
    def render_chat_controls(self):
        """Render chat controls."""
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            current_chat = st.selectbox(
                "Chat attiva",
                options=list(st.session_state.chats.keys()),
                index=list(st.session_state.chats.keys()).index(st.session_state.current_chat)
            )
            if current_chat != st.session_state.current_chat:
                st.session_state.current_chat = current_chat

        with col2:
            if st.button("🆕 Nuova", key="new_chat", use_container_width=True):
                new_chat_name = f"Chat {len(st.session_state.chats) + 1}"
                st.session_state.chats[new_chat_name] = {
                    'messages': [],
                    'created_at': datetime.now().isoformat()
                }
                st.session_state.current_chat = new_chat_name
                st.rerun()

        with col3:
            if st.button("✏️ Rinomina", key="rename_chat", use_container_width=True):
                st.session_state.renaming = True
                st.rerun()

        with col4:
            if len(st.session_state.chats) > 1 and st.button("🗑️ Elimina", key="delete_chat", use_container_width=True):
                del st.session_state.chats[st.session_state.current_chat]
                st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                st.rerun()
    
    def render(self):
        """Render the chat interface."""
        # Render chat controls
        self.render_chat_controls()

        # Handle chat renaming
        if getattr(st.session_state, 'renaming', False):
            with st.form("rename_chat_form"):
                new_name = st.text_input("Nuovo nome", value=st.session_state.current_chat)
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Salva"):
                        if new_name and new_name != st.session_state.current_chat:
                            st.session_state.chats[new_name] = st.session_state.chats.pop(st.session_state.current_chat)
                            st.session_state.current_chat = new_name
                        st.session_state.renaming = False
                        st.rerun()
                with col2:
                    if st.form_submit_button("Annulla"):
                        st.session_state.renaming = False
                        st.rerun()

        # Display chat messages
        for idx, message in enumerate(st.session_state.chats[st.session_state.current_chat]['messages']):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show options for assistant messages
                if message["role"] == "assistant":
                    with st.expander("🔧 Opzioni", expanded=False):
                        timestamp = int(time.time())  # Add timestamp to make keys unique
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("📋 Copia", key=f"copy_{idx}_{timestamp}"):
                                try:
                                    import pyperclip
                                    pyperclip.copy(message['content'])
                                    st.success("Copiato!")
                                except Exception as e:
                                    st.error(f"Errore durante la copia: {str(e)}")
                        with col2:
                            if st.button("🔄 Rigenera", key=f"regen_{idx}_{timestamp}"):
                                # Find last user message
                                user_messages = [msg for msg in st.session_state.chats[st.session_state.current_chat]['messages'] 
                                               if msg["role"] == "user"]
                                if user_messages:
                                    st.session_state.regenerating_message = {
                                        'index': idx,
                                        'prompt': user_messages[-1]["content"]
                                    }
                                    st.rerun()

class CodeViewer:
    """Code viewer component."""
    
    def render(self):
        """Render the code viewer."""
        if st.session_state.get('selected_file'):
            file_info = st.session_state.files[st.session_state.selected_file]
            
            # File info header
            st.markdown(f"**{file_info['name']}** ({file_info['language'].capitalize()})")
            
            # Code display with syntax highlighting
            st.code(file_info['content'], language=file_info['language'])
            
            # File statistics
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Lines", len(file_info['content'].splitlines()))
            with col2:
                st.metric("Size", f"{file_info['size']} bytes")
            with col3:
                st.metric("Language", file_info['language'].capitalize())
        else:
            st.info("Select a file from the sidebar to view its content")

class ModelSelector:
    """Model selector component."""
    
    def render(self):
        """Render the model selector."""
        models = {
            'o1-mini': '🚀 O1 Mini (Fast)',
            'o1-preview': '🔍 O1 Preview (Advanced)',
            'claude-3-5-sonnet-20241022': '🎭 Claude 3.5 Sonnet (Detailed)'
        }
        
        current_model = st.session_state.get('current_model', 'o1-mini')
        
        selected = st.selectbox(
            "Model",
            options=list(models.keys()),
            format_func=lambda x: models[x],
            index=list(models.keys()).index(current_model),
            key="model_selector"
        )
        
        if selected != current_model:
            st.session_state.current_model = selected
            # Clear rate limiting cache on model change
            if 'call_count' in st.session_state:
                st.session_state.call_count = {}
            st.rerun()
            
        # Show model details
        if st.checkbox("Show model details", key="show_model_details"):
            model_info = {
                'o1-mini': {
                    'context': '128K tokens',
                    'best_for': 'Quick fixes, simple analysis',
                    'cost': '$0.001/1K tokens'
                },
                'o1-preview': {
                    'context': '128K tokens',
                    'best_for': 'Complex analysis, architecture review',
                    'cost': '$0.01/1K tokens'
                },
                'claude-3-5-sonnet-20241022': {
                    'context': '200K tokens',
                    'best_for': 'Large codebases, detailed explanations',
                    'cost': '$0.008/1K tokens'
                }
            }
            
            info = model_info[selected]
            st.markdown(f"""
            **Model Details:**
            - Context: {info['context']}
            - Best for: {info['best_for']}
            - Cost: {info['cost']}
            """)

class StatsDisplay:
    """Statistics display component."""
    
    def _format_number(self, num: float) -> str:
        """Format number for display."""
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        return str(int(num))
    
    def render(self):
        """Render the stats display."""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Tokens Used",
                self._format_number(st.session_state.get('token_count', 0))
            )
        
        with col2:
            st.metric(
                "Cost ($)",
                f"${st.session_state.get('cost', 0.0):.3f}"
            )
        
        with col3:
            st.metric(
                "Files",
                len(st.session_state.get('files', {}))
            )
            
        # Show detailed stats
        if st.checkbox("Show detailed statistics", key="show_detailed_stats"):
            st.markdown("### 📊 Detailed Statistics")
            
            # Model usage statistics
            st.markdown("#### Model Usage")
            model_usage = st.session_state.get('model_usage', {
                'o1-mini': 0,
                'o1-preview': 0,
                'claude-3-5-sonnet-20241022': 0
            })
            
            total_usage = sum(model_usage.values()) or 1  # Avoid division by zero
            
            for model, count in model_usage.items():
                percentage = (count / total_usage) * 100
                st.progress(percentage / 100, 
                          text=f"{model}: {count} calls ({percentage:.1f}%)")
            
            # File type distribution
            if st.session_state.files:
                st.markdown("#### File Type Distribution")
                file_types = {}
                total_size = 0
                
                for file_info in st.session_state.files.values():
                    lang = file_info['language']
                    size = file_info['size']
                    file_types[lang] = file_types.get(lang, 0) + 1
                    total_size += size
                
                for lang, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(st.session_state.files)) * 100
                    st.progress(percentage / 100, 
                              text=f"{lang.capitalize()}: {count} files ({percentage:.1f}%)")
                
                st.metric("Total Size", f"{total_size / 1024:.1f} KB")
            
            # Chat statistics
            st.markdown("#### Chat Statistics")
            current_chat = st.session_state.chats[st.session_state.current_chat]
            
            total_messages = len(current_chat['messages'])
            user_messages = len([m for m in current_chat['messages'] if m['role'] == 'user'])
            assistant_messages = len([m for m in current_chat['messages'] if m['role'] == 'assistant'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Messages", total_messages)
            with col2:
                st.metric("User Messages", user_messages)
            with col3:
                st.metric("Assistant Messages", assistant_messages)
            
            # Response time trends (if available)
            if 'response_times' in st.session_state:
                st.markdown("#### Response Time Trends")
                response_times = st.session_state.response_times
                if response_times:
                    avg_time = sum(response_times) / len(response_times)
                    st.metric("Average Response Time", f"{avg_time:.2f}s")
                    
                    # Show trend graph
                    import plotly.graph_objects as go
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(y=response_times, mode='lines', name='Response Time'))
                    fig.update_layout(
                        title="Response Times",
                        xaxis_title="Request #",
                        yaxis_title="Time (s)"
                    )
                    st.plotly_chart(fig, use_container_width=True)

def create_file_tree(files: Dict[str, Dict]) -> Dict:
    """Create a tree structure from flat file list."""
    tree = {}
    for filepath, file_info in files.items():
        current = tree
        parts = filepath.split('/')
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current[part] = file_info
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]
    return tree

class FileAnalyzer:
    """Component for file analysis."""
    
    def _count_lines_by_type(self, content: str) -> Dict[str, int]:
        """Count lines by type (code, comments, blank)."""
        lines = content.split('\n')
        stats = {
            'code': 0,
            'comments': 0,
            'blank': 0
        }
        
        in_multiline_comment = False
        for line in lines:
            line = line.strip()
            
            if not line:
                stats['blank'] += 1
            elif line.startswith(('/*', '/**')) and '*/' not in line:
                in_multiline_comment = True
                stats['comments'] += 1
            elif '*/' in line and in_multiline_comment:
                in_multiline_comment = False
                stats['comments'] += 1
            elif in_multiline_comment:
                stats['comments'] += 1
            elif line.startswith(('#', '//', '<!--')):
                stats['comments'] += 1
            else:
                stats['code'] += 1
                
        return stats
    
    def _analyze_complexity(self, content: str, language: str) -> Dict[str, Any]:
        """Analyze code complexity metrics."""
        metrics = {
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'max_line_length': 0,
            'avg_line_length': 0
        }
        
        lines = content.split('\n')
        total_length = 0
        
        for line in lines:
            # Line length metrics
            line_length = len(line)
            metrics['max_line_length'] = max(metrics['max_line_length'], line_length)
            total_length += line_length
            
            # Language specific metrics
            if language == 'python':
                if 'def ' in line:
                    metrics['functions'] += 1
                elif 'class ' in line:
                    metrics['classes'] += 1
                elif 'import ' in line or 'from ' in line and ' import ' in line:
                    metrics['imports'] += 1
            elif language in ['javascript', 'typescript']:
                if 'function ' in line or '=>' in line:
                    metrics['functions'] += 1
                elif 'class ' in line:
                    metrics['classes'] += 1
                elif 'import ' in line:
                    metrics['imports'] += 1
                    
        if lines:
            metrics['avg_line_length'] = total_length / len(lines)
            
        return metrics
    
    def render(self):
        """Render file analysis component."""
        selected_file = st.session_state.get('selected_file')
        if selected_file and (file_info := st.session_state.files.get(selected_file)):
            st.markdown("### 🔍 File Analysis")
            
            # Basic statistics
            line_stats = self._count_lines_by_type(file_info['content'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Code Lines", line_stats['code'])
            with col2:
                st.metric("Comments", line_stats['comments'])
            with col3:
                st.metric("Blank Lines", line_stats['blank'])
            
            # Complexity metrics
            st.markdown("#### Complexity Metrics")
            metrics = self._analyze_complexity(file_info['content'], file_info['language'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Functions", metrics['functions'])
            with col2:
                st.metric("Classes", metrics['classes'])
            with col3:
                st.metric("Imports", metrics['imports'])
            
            # Readability metrics
            st.markdown("#### Readability")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Max Line Length", metrics['max_line_length'])
            with col2:
                st.metric("Avg Line Length", f"{metrics['avg_line_length']:.1f}")
            
            # Line distribution
            if st.checkbox("Show line distribution"):
                total_lines = sum(line_stats.values())
                st.markdown("#### Line Distribution")
                for category, count in line_stats.items():
                    percentage = (count / total_lines) * 100
                    st.progress(percentage / 100, 
                              text=f"{category.title()}: {count} ({percentage:.1f}%)")
        else:
            st.info("Select a file to view analysis")