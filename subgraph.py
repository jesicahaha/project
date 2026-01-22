from neo4j import GraphDatabase

class Neo4jSubgraphRetriever:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_subgraph_by_text(self, query_text, hops=2, limit=50):
        cypher = f"""
        MATCH (n)
        WHERE n.name CONTAINS $query
        WITH n
        MATCH p = (n)-[*1..{hops}]-(m)
        RETURN p
        LIMIT $limit
        """

        with self.driver.session() as session:
            result = session.run(
                cypher,
                {"query": query_text, "limit": limit}
            )
            paths = [record["p"] for record in result]
            return paths

# ==== 類別外部使用 ====
retriever = Neo4jSubgraphRetriever("bolt://localhost:7687", "neo4j", "neo4j123")
paths = retriever.get_subgraph_by_text("郭欣瑜", hops=2, limit=50)
retriever.close()

for path in paths:
    print([node["name"] for node in path.nodes])
