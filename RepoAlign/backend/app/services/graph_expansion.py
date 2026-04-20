from typing import List, Dict, Any
from app.db.neo4j_driver import get_neo4j_driver

class GraphExpansion:
    def __init__(self):
        self.driver = get_neo4j_driver()

    async def expand_context(self, symbol_names: List[str]) -> Dict[str, Any]:
        """
        Expands the context for a list of symbols by finding their direct neighbors in the graph.
        """
        async with self.driver.session() as session:
            results = await session.execute_read(self._find_neighbors, symbol_names)
        return self._format_results(results)

    @staticmethod
    async def _find_neighbors(tx, symbol_names):
        query = """
        UNWIND $symbol_names AS symbolName
        MATCH (s)
        WHERE s.name = symbolName AND (s:Function OR s:Class)
        // OPTIONAL MATCH for callers
        OPTIONAL MATCH (caller)-[:CALLS]->(s)
        // OPTIONAL MATCH for callees
        OPTIONAL MATCH (s)-[:CALLS]->(callee)
        // Get the file path for all symbols
        OPTIONAL MATCH (file:File)-[:DEFINES]->(s)
        OPTIONAL MATCH (caller_file:File)-[:DEFINES]->(caller)
        OPTIONAL MATCH (callee_file:File)-[:DEFINES]->(callee)
        RETURN 
            s.name AS symbol,
            s.content AS symbol_code,
            file.path AS symbol_path,
            collect(DISTINCT {
                name: caller.name, 
                content: caller.content,
                path: caller_file.path,
                type: 'caller'
            }) AS callers,
            collect(DISTINCT {
                name: callee.name, 
                content: callee.content,
                path: callee_file.path,
                type: 'callee'
            }) AS callees
        """
        result = await tx.run(query, symbol_names=symbol_names)
        return [record.data() async for record in result]

    def _format_results(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Formats the raw Neo4j results into a structured response.
        """
        expanded_context = {}
        for record in records:
            symbol_name = record['symbol']
            if not symbol_name:
                continue
            
            neighbors = {}
            
            # Filter out null entries that can be created by OPTIONAL MATCH
            callers = [c for c in record.get('callers', []) if c and c.get('name')]
            callees = [c for c in record.get('callees', []) if c and c.get('name')]

            for caller in callers:
                if caller['name'] not in neighbors:
                    neighbors[caller['name']] = {
                        "code": caller['content'],
                        "path": caller['path'],
                        "type": "caller"
                    }
            
            for callee in callees:
                if callee['name'] not in neighbors:
                    neighbors[callee['name']] = {
                        "code": callee['content'],
                        "path": callee['path'],
                        "type": "callee"
                    }

            expanded_context[symbol_name] = {
                "code": record['symbol_code'],
                "path": record['symbol_path'],
                "neighbors": neighbors
            }
            
        return expanded_context

    def close(self):
        self.driver.close()
