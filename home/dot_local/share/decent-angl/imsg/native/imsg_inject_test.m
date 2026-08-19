#import <Foundation/Foundation.h>

__attribute__((constructor))
static void imsg_inject_test_init(void) {
    @autoreleasepool {
        NSString *path = @"/Users/admin/.local/share/decent-angl/imsg/inject-test.log";
        NSString *line = [NSString stringWithFormat:@"loaded pid=%d bundle=%@ time=%@\n",
                          [[NSProcessInfo processInfo] processIdentifier],
                          [[NSBundle mainBundle] bundleIdentifier] ?: @"",
                          [NSDate date]];
        NSFileHandle *handle = [NSFileHandle fileHandleForWritingAtPath:path];
        if (!handle) {
            [line writeToFile:path atomically:YES encoding:NSUTF8StringEncoding error:nil];
            return;
        }
        [handle seekToEndOfFile];
        [handle writeData:[line dataUsingEncoding:NSUTF8StringEncoding]];
        [handle closeFile];
    }
}
