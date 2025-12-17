#include <sys/types.h>
#include <unistd.h>
#include <json-c/json_object.h>
#include <json-c/json_tokener.h>

static const char json_test[] = \
"{" \
"	\"int\": 1," \
"	\"array\": [ 1, 2 ]," \
"}";


typedef ssize_t (cheetah_write)(void * ctx, char * buf, size_t nb);
int respond(struct json_object * object, cheetah_write * write, void * ctx);

int main(void)
{
	struct json_object * root = json_tokener_parse(json_test);
	return respond(root, (cheetah_write *)write, (void *)1);
}
