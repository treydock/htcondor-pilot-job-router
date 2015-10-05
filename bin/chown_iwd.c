#include <ftw.h>
#include <sys/stat.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/*
 * This program is dangerous and should not be used - only left as
 * an example of how to fix ownership of files without proper HTCondor
 * job sandboxing.
 */

const int allowed_uid = 20066;
const char *allowed_prefix = "/fdata/spool";

int main(int argc, char **argv) {

	int new_uid, new_gid, ret;
	char *path;

	if (argc < 4) {
		fprintf(stderr, "Too few arguments\n");
		exit(1);
	}

	int uid = getuid();
	//int euid = geteuid();
	//printf("UID=%d,EUID=%d\n", uid, euid);
	new_uid = atoi(argv[1]);
	new_gid = atoi(argv[2]);
	path = argv[3];

	if (strncmp(path, allowed_prefix, strlen(allowed_prefix)) != 0) {
		fprintf(stderr, "Path %s is not under allowed prefix %s\n", path, allowed_prefix);
		exit(1);
	}
	if (uid != allowed_uid) {
		fprintf(stderr, "UID=%d is not allowed UID=%d\n", uid, allowed_uid);
		exit(1);
	}

	seteuid(0);

	int walk_chown(const char *name, const struct stat *status, int type) {
		if (type == FTW_F || type == FTW_D) {
			//printf("chown %d:%d %s\n", new_uid, new_gid, name);
			if (chown(name, new_uid, new_gid) < 0) {
				perror("chown");
				return 1;
			}
		}
		return 0;
	}

	ret = ftw(path, walk_chown, 1);

	exit(ret);
}
