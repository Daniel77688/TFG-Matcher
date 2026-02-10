import sys
import os
import getpass
from typing import Optional, Dict

# Asegurar que el path esté correcto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.auth.auth import AuthSystem

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

class AuthInterface:
    """Interfaz integrada con autenticación, búsqueda y agente IA"""
    
    def __init__(self, search_engine=None, llm=None):
        self.auth = AuthSystem()
        self.current_user: Optional[Dict] = None
        self.search_engine = search_engine
        self.llm = llm
        self.chat_history = []
    
    def show_menu(self):
        """Muestra el menú principal"""
        print("\n" + "="*60)
        print("🎓 SISTEMA DE RECOMENDACIÓN DE TUTORES TFG")
        print("="*60)
        print("1. 📝 Registrarse")
        print("2. 🔑 Iniciar sesión")
        print("3. ❌ Salir")
        print("="*60)
    
    def register_flow(self):
        """Flujo de registro de usuario"""
        print("\n📝 REGISTRO DE NUEVO USUARIO")
        print("-" * 60)
        
        username = input("Usuario: ").strip()
        if not username:
            print("❌ El usuario no puede estar vacío")
            return False
        
        email = input("Email: ").strip()
        if not self.auth.validate_email(email):
            print("❌ Email inválido (formato incorrecto)")
            return False
        
        password = getpass.getpass("Contraseña: ")
        is_valid, error_msg = self.auth.validate_password(password)
        if not is_valid:
            print(f"❌ {error_msg}")
            return False
        
        confirm_password = getpass.getpass("Confirmar contraseña: ")
        if password != confirm_password:
            print("❌ Las contraseñas no coinciden")
            return False
        
        result = self.auth.register(username, email, password)
        
        if result["success"]:
            print(f"\n✅ {result['message']}")
            print(f"👤 Usuario: {result['username']}")
            
            # Completar perfil inicial
            complete = input("\n¿Deseas completar tu perfil ahora? (s/n): ").lower()
            if complete == 's':
                self.current_user = {"id": result["user_id"], "username": result["username"]}
                self.complete_profile_flow()
            
            return True
        else:
            print(f"\n❌ {result['message']}")
            return False
    
    def login_flow(self) -> bool:
        """Flujo de inicio de sesión"""
        print("\n🔑 INICIAR SESIÓN")
        print("-" * 60)
        
        username = input("Usuario: ").strip()
        password = getpass.getpass("Contraseña: ")
        
        result = self.auth.login(username, password)
        
        if result["success"]:
            self.current_user = result["user"]
            
            # Inicializar contexto del agente con perfil completo del usuario
            if self.llm and LANGCHAIN_AVAILABLE:
                context = self._build_agent_context()
                self.chat_history = [SystemMessage(content=context)]
            
            print(f"\n✅ Bienvenido, {self.current_user['username']}! 🎉")
            return True
        else:
            print(f"\n❌ {result['message']}")
            return False
    
    def complete_profile_flow(self):
        """Flujo para completar/actualizar el perfil"""
        if not self.current_user:
            print("❌ Debes iniciar sesión primero")
            return
        
        print("\n📋 COMPLETAR PERFIL")
        print("-" * 60)
        print("(Presiona Enter para dejar en blanco)")
        
        profile_data = {}
        
        full_name = input("\nNombre completo: ").strip()
        if full_name:
            profile_data["full_name"] = full_name
        
        degree = input("Grado/Carrera: ").strip()
        if degree:
            profile_data["degree"] = degree
        
        year = input("Año (1-4): ").strip()
        if year.isdigit():
            profile_data["year"] = int(year)
        
        print("\n💡 Intereses (ej: Machine Learning, Web Development, IA):")
        interests = input("-> ").strip()
        if interests:
            profile_data["interests"] = interests
        
        print("\n💻 Habilidades/Conocimientos (ej: Python, Java, SQL):")
        skills = input("-> ").strip()
        if skills:
            profile_data["skills"] = skills
        
        print("\n📚 Áreas preferidas para TFG (ej: IA, Seguridad, Datos):")
        preferred_areas = input("-> ").strip()
        if preferred_areas:
            profile_data["preferred_areas"] = preferred_areas
        
        if profile_data:
            result = self.auth.update_profile(self.current_user["id"], profile_data)
            if result["success"]:
                print(f"\n✅ {result['message']}")
                
                # Actualizar contexto del agente si está activo
                if self.llm and LANGCHAIN_AVAILABLE:
                    context = self._build_agent_context()
                    self.chat_history = [SystemMessage(content=context)]
                    print("🤖 El agente IA ha sido actualizado con tu nuevo perfil")
            else:
                print(f"\n❌ {result['message']}")
        else:
            print("\n⚠️ No se actualizó ningún campo")
    
    def show_profile(self):
        """Muestra el perfil del usuario actual"""
        if not self.current_user:
            print("❌ Debes iniciar sesión primero")
            return
        
        profile = self.auth.get_profile(self.current_user["id"])
        
        if profile:
            print("\n" + "="*60)
            print("👤 TU PERFIL")
            print("="*60)
            print(f"Usuario: {profile['username']}")
            print(f"Email: {profile['email']}")
            print(f"Miembro desde: {profile['created_at']}")
            
            if profile.get('full_name'):
                print(f"\nNombre: {profile['full_name']}")
            if profile.get('degree'):
                print(f"Grado: {profile['degree']}")
            if profile.get('year'):
                print(f"Año: {profile['year']}")
            if profile.get('interests'):
                print(f"\n🎯 Intereses: {profile['interests']}")
            if profile.get('skills'):
                print(f"💻 Habilidades: {profile['skills']}")
            if profile.get('preferred_areas'):
                print(f"📚 Áreas preferidas: {profile['preferred_areas']}")
            
            print("="*60)
        else:
            print("❌ No se pudo cargar el perfil")
    
    def _build_agent_context(self) -> str:
        """Construye un contexto completo y rico para el agente IA"""
        profile = self.auth.get_profile(self.current_user["id"])
        
        # Contexto base
        context = """Eres un asistente inteligente especializado en ayudar a estudiantes universitarios a encontrar tema para su Trabajo de Fin de Grado y un tutor que pueda ayudarle (TFG).

Tu objetivo principal es:
1. Recomendar tutores que se ajusten al perfil e intereses del estudiante
2. Sugerir ideas de proyectos de TFG relevantes y actuales
3. Proporcionar información detallada sobre profesores y sus áreas de investigación
4. Ayudar al estudiante a tomar decisiones informadas sobre su TFG

"""
        
        # Agregar información del estudiante
        context += "=== INFORMACIÓN DEL ESTUDIANTE ===\n"
        context += f"Usuario: {self.current_user['username']}\n"
        
        if profile:
            if profile.get('full_name'):
                context += f"Nombre: {profile['full_name']}\n"
            if profile.get('degree'):
                context += f"Grado/Carrera: {profile['degree']}\n"
            if profile.get('year'):
                context += f"Año académico: {profile['year']}\n"
            
            context += "\n"
            
            if profile.get('interests'):
                context += f"🎯 INTERESES DEL ESTUDIANTE: {profile['interests']}\n"
                context += "   → Usa esta información para recomendar profesores y temas relacionados\n\n"
            
            if profile.get('skills'):
                context += f"💻 HABILIDADES Y CONOCIMIENTOS: {profile['skills']}\n"
                context += "   → Considera estas habilidades al sugerir proyectos técnicos\n\n"
            
            if profile.get('preferred_areas'):
                context += f"📚 ÁREAS PREFERIDAS: {profile['preferred_areas']}\n"
                context += "   → Prioriza tutores especializados en estas áreas\n\n"
        
        # Agregar información de la base de datos si está disponible
        if self.search_engine:
            try:
                stats = self.search_engine.get_database_stats()
                context += "=== INFORMACIÓN DE LA BASE DE DATOS ===\n"
                context += f"Tienes acceso a información de {stats['total_profesores']} profesores y {stats['total_documents']} trabajos académicos.\n"
                
                # Top áreas de investigación
                if stats.get('categorias_populares'):
                    top_areas = list(stats['categorias_populares'].keys())[:5]
                    context += f"Áreas de investigación principales: {', '.join(top_areas)}\n"
                
                # Años de cobertura
                if stats.get('años_cubiertos'):
                    context += f"Datos desde {stats['años_cubiertos'][-1]} hasta {stats['años_cubiertos'][0]}\n"
                
                context += "\n"
            except Exception as e:
                pass
        
        # Instrucciones específicas de comportamiento

        context += """=== CONTROL DE RESPUESTAS ===
        - Responde siempre de forma concisa y directa
        - No generes emails, mensajes formales ni plantillas salvo petición explícita
        - No propongas pasos adicionales si no se solicitan
        - No asumas intención de contacto o acción
        - Prioriza respuestas breves (3–6 líneas)
        - Usa listas solo cuando aporten claridad
        - Evita explicaciones largas o genéricas

        === INTERPRETACIÓN DE INTENCIÓN ===
        - Preguntas "qué / cuál / quién": respuesta informativa y breve
        - Preguntas "cómo / recomiendas": respuesta práctica pero concisa
        - Solo sé proactivo si el usuario lo pide explícitamente
        - Amplía solo si el usuario pide "detalle" o "explícalo más"

        === INSTRUCCIONES DE COMPORTAMIENTO ===
        - Cuando el estudiante pregunte por recomendaciones, considera SIEMPRE su perfil (intereses, habilidades, áreas preferidas)
        - Si el estudiante no tiene perfil completo, sugiérele que lo complete para mejores recomendaciones
        - Da respuestas concretas y prácticas, no solo teoría
        - Si no tienes información específica sobre algo, sé honesto y sugiere usar la función de búsqueda

        IMPORTANTE: Este estudiante te está pidiendo ayuda personalizada. Usa toda su información de perfil en tus recomendaciones.
        """
        
        return context
    
    # ========== BÚSQUEDA DE PROFESORES ==========
    
    def search_interface(self):
        """Interfaz de búsqueda integrada"""
        if not self.search_engine:
            print("\n❌ El motor de búsqueda no está disponible")
            print("💡 Ejecuta: python src/data/data_loader.py para cargar los datos")
            input("\nPresiona Enter para continuar...")
            return
        
        while True:
            print("\n" + "="*60)
            print("🔍 BÚSQUEDA DE PROFESORES Y TRABAJOS")
            print("="*60)
            print("1. 🎯 Búsqueda por palabras clave")
            print("2. 👨‍🏫 Buscar por profesor específico")
            print("3. 📋 Ver todos los profesores")
            print("4. 🏆 Ver perfil detallado de profesor")
            print("5. 📊 Estadísticas de la base de datos")
            print("6. 🔙 Volver al menú principal")
            print("="*60)
            
            opcion = input("\nSelecciona una opción: ").strip()
            
            if opcion == "1":
                self._search_by_keywords()
            elif opcion == "2":
                self._search_by_professor()
            elif opcion == "3":
                self._show_all_professors()
            elif opcion == "4":
                self._show_professor_profile()
            elif opcion == "5":
                self._show_database_stats()
            elif opcion == "6":
                break
            else:
                print("❌ Opción inválida")
    
    def _search_by_keywords(self):
        """Búsqueda por palabras clave"""
        print("\n🎯 BÚSQUEDA POR PALABRAS CLAVE")
        query = input("Ingresa tus palabras clave: ").strip()
        
        if not query:
            print("❌ Debes ingresar al menos una palabra clave")
            input("\nPresiona Enter para continuar...")
            return
        
        try:
            limit = int(input("Número máximo de resultados (default 10): ") or "10")
        except:
            limit = 10
        
        print(f"\n🔍 Buscando: '{query}'...")
        resultados = self.search_engine.search(query=query, limit=limit)
        
        # Guardar en historial
        if self.current_user:
            self.auth.add_search_history(self.current_user["id"], query, "keywords")
        
        self._display_search_results(resultados)
    
    def _search_by_professor(self):
        """Búsqueda por profesor"""
        print("\n👨‍🏫 BÚSQUEDA POR PROFESOR")
        profesor = input("Nombre del profesor: ").strip()
        
        if not profesor:
            print("❌ Debes ingresar un nombre de profesor")
            input("\nPresiona Enter para continuar...")
            return
        
        resultados = self.search_engine.search(
            query="",
            filters={"profesor": profesor},
            limit=20
        )
        
        # Guardar en historial
        if self.current_user:
            self.auth.add_search_history(self.current_user["id"], f"Profesor: {profesor}", "professor")
        
        self._display_search_results(resultados)
    
    def _show_all_professors(self):
        """Mostrar todos los profesores"""
        print("\n📋 LISTA DE PROFESORES")
        profesores = self.search_engine.get_all_profesores()
        
        print(f"\n👥 Total de profesores: {profesores['total_profesores']}")
        print("\n" + "-"*80)
        print(f"{'#':<5} {'NOMBRE':<40} {'TRABAJOS':<10}")
        print("-"*80)
        
        for i, profesor in enumerate(profesores['profesores'][:50], 1):
            print(f"{i:<5} {profesor['name']:<40} {profesor['total_works']:<10}")
        
        if len(profesores['profesores']) > 50:
            print(f"\n... y {len(profesores['profesores']) - 50} profesores más")
        
        input("\n📝 Presiona Enter para continuar...")
    
    def _show_professor_profile(self):
        """Mostrar perfil detallado de profesor"""
        print("\n🏆 PERFIL DE PROFESOR")
        profesor = input("Nombre del profesor: ").strip()
        
        if not profesor:
            print("❌ Debes ingresar un nombre de profesor")
            input("\nPresiona Enter para continuar...")
            return
        
        perfil = self.search_engine.get_profesor_profile(profesor)
        
        if not perfil:
            print(f"❌ No se encontró el profesor '{profesor}'")
            input("\nPresiona Enter para continuar...")
            return
        
        stats = perfil['estadisticas']
        
        print(f"\n{'='*70}")
        print(f"👨‍🏫 PERFIL: {perfil['profesor']}")
        print(f"{'='*70}")
        print(f"\n📊 ESTADÍSTICAS:")
        print(f"   • Total de trabajos: {stats['total_trabajos']}")
        
        if stats['años_activo']:
            años = ', '.join(stats['años_activo'][:10])
            print(f"   • Años activo: {años}")
            if len(stats['años_activo']) > 10:
                print(f"     ... y {len(stats['años_activo']) - 10} años más")
        
        if stats['categorias']:
            cats = ', '.join(stats['categorias'][:5])
            print(f"   • Categorías: {cats}")
            if len(stats['categorias']) > 5:
                print(f"     ... y {len(stats['categorias']) - 5} más")
        
        print(f"\n📈 DISTRIBUCIÓN POR TIPO:")
        for tipo, count in stats['tipos_produccion'].items():
            print(f"   • {tipo}: {count} trabajos")
        
        print(f"\n🎯 TRABAJOS MÁS RECIENTES:")
        for i, trabajo in enumerate(stats['trabajos_recientes'][:5], 1):
            print(f"\n   {i}. {trabajo['titulo'][:65]}...")
            print(f"      📅 {trabajo['fecha']} | 🏷️ {trabajo['tipo_produccion']}")
            if trabajo.get('if_sjr'):
                print(f"      ⭐ IF: {trabajo['if_sjr']} | 📊 Q: {trabajo.get('q_sjr', 'N/A')}")
        
        input("\n📝 Presiona Enter para continuar...")
    
    def _show_database_stats(self):
        """Mostrar estadísticas de la base de datos"""
        stats = self.search_engine.get_database_stats()
        
        print(f"\n{'='*70}")
        print("📊 ESTADÍSTICAS DE LA BASE DE DATOS")
        print(f"{'='*70}")
        
        print(f"\n📄 DOCUMENTACIÓN:")
        print(f"   • Total documentos: {stats['total_documents']}")
        print(f"   • Total profesores: {stats['total_profesores']}")
        
        if stats['total_profesores'] > 0:
            ratio = stats['total_documents'] / stats['total_profesores']
            print(f"   • Ratio documentos/profesor: {ratio:.1f}")
        
        print(f"\n🏆 TOP 10 TIPOS DE PRODUCCIÓN:")
        for tipo, count in list(stats['tipos_produccion'].items())[:10]:
            porcentaje = (count / stats['total_documents']) * 100 if stats['total_documents'] > 0 else 0
            print(f"   • {tipo:<30} {count:>4} ({porcentaje:.1f}%)")
        
        print(f"\n📅 LÍNEA TEMPORAL:")
        if stats['años_cubiertos']:
            print(f"   • Años cubiertos: {len(stats['años_cubiertos'])} años")
            print(f"   • Desde: {stats['años_cubiertos'][-1]}")
            print(f"   • Hasta: {stats['años_cubiertos'][0]}")
        
        input("\n📝 Presiona Enter para continuar...")
    
    def _display_search_results(self, resultados):
        """Mostrar resultados de búsqueda"""
        print(f"\n{'='*80}")
        print(f"🎯 RESULTADOS: '{resultados['query']}'")
        print(f"📊 Encontrados: {resultados['total_results']} resultados")
        print(f"{'='*80}")
        
        if not resultados['results']:
            print("\n😞 No se encontraron resultados que coincidan con tu búsqueda")
            input("\n📝 Presiona Enter para continuar...")
            return
        
        for i, resultado in enumerate(resultados['results'], 1):
            print(f"\n🏆 RESULTADO {i}:")
            print(f"   👨‍🏫 Profesor: {resultado['profesor']}")
            print(f"   📝 Título: {resultado['titulo'][:65]}...")
            print(f"   🎯 Tipo: {resultado['tipo_produccion']}")
            print(f"   📅 Fecha: {resultado['fecha']}")
            
            if resultado.get('if_sjr'):
                print(f"   ⭐ Factor de Impacto: {resultado['if_sjr']}")
            if resultado.get('q_sjr'):
                print(f"   📊 Cuartil SJR: {resultado['q_sjr']}")
            
            print(f"   📈 Relevancia: {resultado['relevance_score']:.3f}")
            
            if resultado.get('categorias'):
                print(f"   🔍 Categorías: {resultado['categorias']}")
            
            print("   " + "-" * 75)
        
        input("\n📝 Presiona Enter para continuar...")
    
    # ========== AGENTE IA ==========
    
    def chat_interface(self):
        """Interfaz de chat con el agente IA"""
        if not self.llm or not LANGCHAIN_AVAILABLE:
            print("\n❌ El agente IA no está disponible")
            print("💡 Verifica:")
            print("   1. Credenciales de OpenRouter en .env")
            print("   2. Instalación de langchain: pip install langchain-openai")
            input("\nPresiona Enter para continuar...")
            return
        
        # Verificar si el usuario tiene perfil completo
        profile = self.auth.get_profile(self.current_user["id"])
        has_profile = bool(profile and (profile.get('interests') or profile.get('skills') or profile.get('preferred_areas')))
        
        print("\n" + "="*60)
        print("🤖 AGENTE IA - ASISTENTE DE TFG PERSONALIZADO")
        print("="*60)
        
        if not has_profile:
            print("\n⚠️  RECOMENDACIÓN: Completa tu perfil para recomendaciones personalizadas")
            print("   El agente funcionará mejor si conoce tus intereses y habilidades")
            complete = input("\n¿Quieres completar tu perfil ahora? (s/n): ").lower()
            if complete == 's':
                self.complete_profile_flow()
                print("\n✅ Perfil actualizado. Iniciando chat...")
        
        print("\nEscribe 'salir' para volver al menú principal")
        print("Escribe 'contexto' para ver qué información tiene el agente sobre ti")
        print("\n💡 El agente puede ayudarte con:")
        print("   • Recomendaciones personalizadas de tutores")
        print("   • Ideas de proyectos de TFG basadas en tu perfil")
        print("   • Información sobre profesores y sus investigaciones")
        print("   • Consejos para elegir tu TFG")
        print("="*60 + "\n")
        
        while True:
            try:
                pregunta = input("💬 Tú: ").strip()
                
                if pregunta.lower() in ['salir', 'exit', 'quit', 'volver']:
                    print("\n👋 Volviendo al menú principal...")
                    break
                
                if pregunta.lower() == 'contexto':
                    self._show_agent_context()
                    continue
                
                if not pregunta:
                    continue
                
                # Añadir mensaje del usuario
                self.chat_history.append(HumanMessage(content=pregunta))
                
                # Obtener respuesta
                print("\n🤖 Agente: ", end="", flush=True)
                respuesta = self.llm.invoke(self.chat_history)
                
                # Añadir respuesta al historial
                self.chat_history.append(respuesta)
                
                print(respuesta.content + "\n")
                
                # Guardar en historial
                if self.current_user:
                    self.auth.add_search_history(self.current_user["id"], pregunta, "agente_ia")
                
            except KeyboardInterrupt:
                print("\n\n👋 Volviendo al menú principal...")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                print("💡 Intenta de nuevo o escribe 'salir' para volver\n")
    
    def _show_agent_context(self):
        """Muestra el contexto que tiene el agente sobre el usuario"""
        profile = self.auth.get_profile(self.current_user["id"])
        
        print("\n" + "="*60)
        print("🔍 CONTEXTO DEL AGENTE IA")
        print("="*60)
        print("\nEl agente tiene acceso a la siguiente información sobre ti:\n")
        
        if profile:
            if profile.get('full_name'):
                print(f"✅ Nombre: {profile['full_name']}")
            if profile.get('degree'):
                print(f"✅ Grado: {profile['degree']}")
            if profile.get('year'):
                print(f"✅ Año: {profile['year']}")
            if profile.get('interests'):
                print(f"✅ Intereses: {profile['interests']}")
            if profile.get('skills'):
                print(f"✅ Habilidades: {profile['skills']}")
            if profile.get('preferred_areas'):
                print(f"✅ Áreas preferidas: {profile['preferred_areas']}")
        
        if self.search_engine:
            stats = self.search_engine.get_database_stats()
            print(f"\n✅ Base de datos: {stats['total_profesores']} profesores, {stats['total_documents']} trabajos")
        
        print("\n💡 El agente usa esta información para darte recomendaciones personalizadas")
        print("="*60 + "\n")
    
    # ========== MENÚ PRINCIPAL ==========
    
    def user_menu(self):
        """Menú del usuario logueado"""
        while True:
            print("\n" + "="*60)
            print(f"👤 USUARIO: {self.current_user['username']}")
            print("="*60)
            print("1. 🔍 Buscar profesores")
            print("2. 🤖 Agente IA (Chat)")
            print("3. 👤 Ver mi perfil")
            print("4. ✏️  Editar perfil")
            print("5. 🚪 Cerrar sesión")
            print("="*60)
            
            opcion = input("\nSelecciona una opción: ").strip()
            
            if opcion == "1":
                self.search_interface()
            elif opcion == "2":
                self.chat_interface()
            elif opcion == "3":
                self.show_profile()
                input("\nPresiona Enter para continuar...")
            elif opcion == "4":
                self.complete_profile_flow()
            elif opcion == "5":
                print(f"\n👋 Hasta luego, {self.current_user['username']}!")
                self.current_user = None
                self.chat_history = []
                break
            else:
                print("❌ Opción inválida")
    
    def run(self):
        """Ejecuta la aplicación principal"""
        while True:
            if self.current_user:
                self.user_menu()
            else:
                self.show_menu()
                opcion = input("\nSelecciona una opción: ").strip()
                
                if opcion == "1":
                    self.register_flow()
                elif opcion == "2":
                    if self.login_flow():
                        continue
                elif opcion == "3":
                    print("\n👋 ¡Hasta pronto!")
                    break
                else:
                    print("❌ Opción inválida")