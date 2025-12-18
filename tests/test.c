#include <sys/types.h>
#include <unistd.h>
#include <json-c/json_object.h>
#include <json-c/json_util.h>

typedef ssize_t (cheetah_write)(void * ctx, char * buf, size_t nb);
int respond(struct json_object * object, cheetah_write * write, void * ctx);

int main(int argc, char **argv)
{
	struct json_object * root = json_object_from_file(argv[1]);
	return respond(root, (cheetah_write *)write, (void *)1);
}
