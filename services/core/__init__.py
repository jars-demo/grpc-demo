"""Transport-independent business logic shared by the gRPC server and the REST API.

Nothing in this package knows about gRPC, HTTP, or TLS. Both interfaces call the same functions,
which is what makes the REST-versus-gRPC comparison fair.
"""
