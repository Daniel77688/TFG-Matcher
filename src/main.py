from src.data.data_processor_pandas import DataProcessorPandas, get_chroma_collection
from src.search.search_engine import SearchEngine
import sys
import os

class SuperMain:
    def __init__(self):
        self.search_engine = None
        self.initialize_system()
    
    def initialize_system(self):
        """Inicializar el sistema de búsqueda"""
        print("🔧 INICIALIZANDO SISTEMA DE BÚSQUEDA...")
        try:
            # Usar el método estático para obtener la colección
            coleccion = get_chroma_collection()
            if not coleccion:
                print("❌ ERROR: No se pudo cargar la colección de ChromaDB")
                print("💡 Ejecuta primero: python data_loader.py")
                return False
            
            self.search_engine = SearchEngine(coleccion)
            print("✅ Sistema de búsqueda inicializado correctamente")
            
            # Mostrar stats iniciales
            self.show_initial_stats()
            return True
            
        except Exception as e:
            print(f"❌ Error inicializando el sistema: {e}")
            return False
    
    def show_initial_stats(self):
        """Mostrar estadísticas iniciales del sistema"""
        stats = self.search_engine.get_database_stats()
        print("\n" + "="*60)
        print("📊 ESTADÍSTICAS DE LA BASE DE DATOS")
        print("="*60)
        print(f"📄 Total de documentos: {stats['total_documents']}")
        print(f"👨‍🏫 Total de profesores: {stats['total_profesores']}")
        
        if stats['años_cubiertos']:
            print(f"📅 Años cubiertos: {', '.join(stats['años_cubiertos'][:10])}{'...' if len(stats['años_cubiertos']) > 10 else ''}")
        
        print("\n🏆 Tipos de producción más comunes:")
        for tipo, count in list(stats['tipos_produccion'].items())[:5]:
            print(f"   - {tipo}: {count}")

    def search_interface(self):
        """Interfaz de búsqueda interactiva"""
        while True:
            print("\n" + "🔍"*30)
            print("        INTERFAZ DE BÚSQUEDA")
            print("🔍"*30)
            print("1. 🔎 Búsqueda por palabras clave")
            print("2. 👨‍🏫 Búsqueda por profesor")
            print("3. 📊 Ver todos los profesores")
            print("4. 🏆 Ver perfil de profesor")
            print("5. 📈 Estadísticas avanzadas")
            print("6. 🚪 Salir")
            
            opcion = input("\nSelecciona una opción (1-6): ").strip()
            
            if opcion == "1":
                self.search_by_keywords()
            elif opcion == "2":
                self.search_by_professor()
            elif opcion == "3":
                self.show_all_professors()
            elif opcion == "4":
                self.show_professor_profile()
            elif opcion == "5":
                self.show_advanced_stats()
            elif opcion == "6":
                print("👋 ¡Hasta pronto!")
                break
            else:
                print("❌ Opción no válida. Intenta de nuevo.")
    
    def search_by_keywords(self):
        """Búsqueda por palabras clave con filtros"""
        print("\n🎯 BÚSQUEDA POR PALABRAS CLAVE")
        query = input("Ingresa tus palabras clave: ").strip()
        
        if not query:
            print("❌ Debes ingresar al menos una palabra clave")
            return
        
        # Opciones de filtrado
        filters = {}
        
        print("\n🎛️  OPCIONES DE FILTRADO (opcional):")
        profesor = input("Filtrar por profesor (dejar vacío para todos): ").strip()
        if profesor:
            filters["profesor"] = profesor
        
        tipo = input("Filtrar por tipo de producción (Artículo, Conferencia, etc.): ").strip()
        if tipo:
            filters["tipo_produccion"] = tipo
        
        cuartil = input("Filtrar por cuartil SJR (Q1, Q2, Q3, Q4): ").strip()
        if cuartil:
            filters["q_sjr"] = cuartil
        
        try:
            limit = int(input("Número máximo de resultados (default 10): ") or "10")
        except:
            limit = 10
        
        # Realizar búsqueda
        print(f"\n🔍 Buscando: '{query}'...")
        resultados = self.search_engine.search(
            query=query,
            limit=limit,
            filters=filters if filters else None
        )
        
        self.display_search_results(resultados)
    
    def search_by_professor(self):
        """Búsqueda específica por profesor"""
        print("\n👨‍🏫 BÚSQUEDA POR PROFESOR")
        profesor = input("Nombre del profesor: ").strip()
        
        if not profesor:
            print("❌ Debes ingresar un nombre de profesor")
            return
        
        # Primero verificamos si el profesor existe
        profesores = self.search_engine.get_all_profesores()
        profesor_encontrado = any(p['name'].lower() == profesor.lower() for p in profesores['profesores'])
        
        if not profesor_encontrado:
            print(f"❌ Profesor '{profesor}' no encontrado")
            print("💡 Algunos profesores disponibles:")
            for p in profesores['profesores'][:10]:
                print(f"   - {p['name']}")
            return
        
        query = input("Palabras clave específicas (opcional): ").strip()
        
        resultados = self.search_engine.search(
            query=query or "",
            filters={"profesor": profesor},
            limit=20
        )
        
        self.display_search_results(resultados)
    
    def show_all_professors(self):
        """Mostrar todos los profesores con estadísticas"""
        print("\n📋 LISTA COMPLETA DE PROFESORES")
        profesores = self.search_engine.get_all_profesores()
        
        print(f"\n👥 Total de profesores: {profesores['total_profesores']}")
        print("\n" + "-"*80)
        print(f"{'NOMBRE':<30} {'TRABAJOS':<10} {'TIPOS DE PRODUCCIÓN'}")
        print("-"*80)
        
        for profesor in profesores['profesores']:
            tipos = ", ".join(list(profesor['work_types'].keys())[:3])
            if len(profesor['work_types']) > 3:
                tipos += "..."
            print(f"{profesor['name']:<30} {profesor['total_works']:<10} {tipos}")
        
        input("\n📝 Presiona Enter para continuar...")
    
    def show_professor_profile(self):
        """Mostrar perfil detallado de un profesor"""
        print("\n🏆 PERFIL DE PROFESOR")
        profesor = input("Nombre del profesor: ").strip()
        
        if not profesor:
            print("❌ Debes ingresar un nombre de profesor")
            return
        
        perfil = self.search_engine.get_profesor_profile(profesor)
        
        if not perfil:
            print(f"❌ No se encontró el profesor '{profesor}'")
            return
        
        print(f"\n{'='*60}")
        print(f"👨‍🏫 PERFIL: {perfil['profesor']}")
        print(f"{'='*60}")
        
        stats = perfil['estadisticas']
        print(f"📊 ESTADÍSTICAS:")
        print(f"   • Total de trabajos: {stats['total_trabajos']}")
        if stats['años_activo']:
            print(f"   • Años activo: {', '.join(stats['años_activo'][:10])}")
        if stats['categorias']:
            print(f"   • Categorías: {', '.join(stats['categorias'][:5])}")
            if len(stats['categorias']) > 5:
                print(f"     ... y {len(stats['categorias']) - 5} más")
        
        print(f"\n📈 DISTRIBUCIÓN POR TIPO:")
        for tipo, count in stats['tipos_produccion'].items():
            print(f"   • {tipo}: {count} trabajos")
        
        print(f"\n🎯 TRABAJOS MÁS RECIENTES:")
        for i, trabajo in enumerate(stats['trabajos_recientes'][:5], 1):
            print(f"   {i}. {trabajo['titulo']}")
            print(f"      📅 {trabajo['fecha']} | 🏷️ {trabajo['tipo_produccion']}")
            if trabajo.get('if_sjr'):
                print(f"      ⭐ IF: {trabajo['if_sjr']} | 📊 Q: {trabajo.get('q_sjr', 'N/A')}")
            print()
        
        input("📝 Presiona Enter para continuar...")
    
    def show_advanced_stats(self):
        """Mostrar estadísticas avanzadas del sistema"""
        print("\n📈 ESTADÍSTICAS AVANZADAS")
        stats = self.search_engine.get_database_stats()
        
        print(f"\n📄 DOCUMENTACIÓN:")
        print(f"   • Total documentos: {stats['total_documents']}")
        print(f"   • Total profesores: {stats['total_profesores']}")
        if stats['total_profesores'] > 0:
            ratio = stats['total_documents'] / stats['total_profesores']
            print(f"   • Ratio documentos/profesor: {ratio:.1f}")
        
        print(f"\n🏆 TOP 10 TIPOS DE PRODUCCIÓN:")
        for tipo, count in list(stats['tipos_produccion'].items())[:10]:
            porcentaje = (count / stats['total_documents']) * 100 if stats['total_documents'] > 0 else 0
            print(f"   • {tipo:<25} {count:>4} ({porcentaje:.1f}%)")
        
        print(f"\n📊 CATEGORÍAS MÁS POPULARES:")
        for categoria, count in list(stats['categorias_populares'].items())[:10]:
            print(f"   • {categoria:<30} {count:>4}")
        
        print(f"\n📅 LINEA TEMPORAL:")
        if stats['años_cubiertos']:
            print(f"   • Años cubiertos: {len(stats['años_cubiertos'])} años")
            print(f"   • Desde: {stats['años_cubiertos'][-1]}")
            print(f"   • Hasta: {stats['años_cubiertos'][0]}")
        else:
            print("   • No hay datos de fechas")
        
        input("\n📝 Presiona Enter para continuar...")
    
    def display_search_results(self, resultados):
        """Mostrar resultados de búsqueda de forma formateada"""
        print(f"\n🎯 RESULTADOS DE BÚSQUEDA: '{resultados['query']}'")
        print(f"📊 Encontrados: {resultados['total_results']} resultados")
        
        if resultados['filters_applied']:
            print(f"🎛️  Filtros aplicados: {resultados['filters_applied']}")
        
        print("\n" + "="*100)
        
        if not resultados['results']:
            print("😞 No se encontraron resultados que coincidan con tu búsqueda")
            return
        
        for i, resultado in enumerate(resultados['results'], 1):
            print(f"\n🏆 RESULTADO {i}:")
            print(f"   👨‍🏫 Profesor: {resultado['profesor']}")
            print(f"   📝 Título: {resultado['titulo']}")
            print(f"   🎯 Tipo: {resultado['tipo_produccion']}")
            print(f"   📅 Fecha: {resultado['fecha']}")
            if resultado.get('if_sjr'):
                print(f"   ⭐ Factor de Impacto: {resultado['if_sjr']}")
            if resultado.get('q_sjr'):
                print(f"   📊 Cuartil SJR: {resultado['q_sjr']}")
            print(f"   📈 Relevancia: {resultado['relevance_score']:.3f}")
            if resultado['categorias']:
                print(f"   🔍 Categorías: {resultado['categorias']}")
            if resultado['fuente']:
                print(f"   📚 Fuente: {resultado['fuente']}")
            print("   " + "-" * 80)
        
        input("\n📝 Presiona Enter para continuar...")
    
    def run_demo_queries(self):
        """Ejecutar consultas de demostración automáticas"""
        print("\n🚀 EJECUTANDO CONSULTAS DE DEMOSTRACIÓN")
        
        demos = [
            {"query": "machine learning", "filters": {}, "desc": "Búsqueda general de ML"},
            {"query": "artificial intelligence", "filters": {"q_sjr": "Q1"}, "desc": "AI en revistas Q1"},
            {"query": "deep learning", "filters": {"tipo_produccion": "Conferencia"}, "desc": "DL en conferencias"},
            {"query": "", "filters": {}, "desc": "Búsqueda vacía (todos los documentos)"},
        ]
        
        for demo in demos:
            print(f"\n🎯 DEMO: {demo['desc']}")
            print("="*50)
            
            resultados = self.search_engine.search(
                query=demo["query"],
                filters=demo["filters"] if demo["filters"] else None,
                limit=3
            )
            
            if resultados['results']:
                for i, res in enumerate(resultados['results'][:2], 1):
                    print(f"   {i}. {res['profesor']} - {res['titulo'][:60]}... (Score: {res['relevance_score']:.3f})")
            else:
                print("   😞 No se encontraron resultados")
        
        input("\n📝 Presiona Enter para volver al menú principal...")

def main():
    """Función principal"""
    print("🚀 SUPER MAIN - SISTEMA DE BÚSQUEDA ACADÉMICA")
    print("="*60)
    
    app = SuperMain()
    
    # Verificar si el sistema se inicializó correctamente
    if not app.search_engine:
        print("❌ No se pudo inicializar el sistema de búsqueda")
        return
    
    while True:
        print("\n" + "⭐"*30)
        print("        MENÚ PRINCIPAL")
        print("⭐"*30)
        print("1. 🎯 Interfaz de Búsqueda Interactiva")
        print("2. 🚀 Ejecutar Demostración Automática")
        print("3. 📊 Ver Estadísticas Rápidas")
        print("4. 🚪 Salir")
        
        opcion = input("\nSelecciona una opción (1-4): ").strip()
        
        if opcion == "1":
            app.search_interface()
        elif opcion == "2":
            app.run_demo_queries()
        elif opcion == "3":
            app.show_initial_stats()
        elif opcion == "4":
            print("👋 ¡Gracias por usar el sistema! ¡Hasta pronto!")
            break
        else:
            print("❌ Opción no válida. Intenta de nuevo.")

if __name__ == "__main__":
    main()