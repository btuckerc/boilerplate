#import <AppKit/AppKit.h>
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <objc/message.h>
#import <objc/runtime.h>

static NSString *ArgValue(NSArray<NSString *> *args, NSString *flag, NSString *fallback) {
    NSUInteger index = [args indexOfObject:flag];
    if (index == NSNotFound || index + 1 >= [args count]) {
        return fallback;
    }
    return args[index + 1];
}

static NSArray<NSString *> *SelectorNamesForClass(Class cls, BOOL classMethods) {
    unsigned int count = 0;
    Method *methods = class_copyMethodList(classMethods ? object_getClass(cls) : cls, &count);
    NSMutableArray<NSString *> *names = [NSMutableArray array];
    for (unsigned int index = 0; index < count; index += 1) {
        SEL sel = method_getName(methods[index]);
        if (sel) {
            [names addObject:NSStringFromSelector(sel)];
        }
    }
    free(methods);
    [names sortUsingSelector:@selector(compare:)];
    return names;
}

static NSArray<NSDictionary *> *PropertiesForClass(Class cls) {
    unsigned int count = 0;
    objc_property_t *properties = class_copyPropertyList(cls, &count);
    NSMutableArray<NSDictionary *> *items = [NSMutableArray array];
    for (unsigned int index = 0; index < count; index += 1) {
        const char *name = property_getName(properties[index]);
        const char *attributes = property_getAttributes(properties[index]);
        [items addObject:@{
            @"name": name ? [NSString stringWithUTF8String:name] : @"",
            @"attributes": attributes ? [NSString stringWithUTF8String:attributes] : @"",
        }];
    }
    free(properties);
    return items;
}

static NSString *TypeEncodingString(const char *types) {
    if (!types) {
        return @"";
    }
    return [NSString stringWithUTF8String:types] ?: @"";
}

static NSArray<NSDictionary *> *MethodDescriptionsForProtocol(Protocol *protocol, BOOL required, BOOL instanceMethods) {
    unsigned int count = 0;
    struct objc_method_description *descriptions =
        protocol_copyMethodDescriptionList(protocol, required, instanceMethods, &count);
    NSMutableArray<NSDictionary *> *items = [NSMutableArray array];
    for (unsigned int index = 0; index < count; index += 1) {
        SEL sel = descriptions[index].name;
        [items addObject:@{
            @"name": sel ? NSStringFromSelector(sel) : @"",
            @"types": TypeEncodingString(descriptions[index].types),
        }];
    }
    free(descriptions);
    [items sortUsingComparator:^NSComparisonResult(NSDictionary *lhs, NSDictionary *rhs) {
        return [lhs[@"name"] compare:rhs[@"name"]];
    }];
    return items;
}

static NSArray<NSDictionary *> *PropertiesForProtocol(Protocol *protocol) {
    unsigned int count = 0;
    objc_property_t *properties = protocol_copyPropertyList(protocol, &count);
    NSMutableArray<NSDictionary *> *items = [NSMutableArray array];
    for (unsigned int index = 0; index < count; index += 1) {
        const char *name = property_getName(properties[index]);
        const char *attributes = property_getAttributes(properties[index]);
        [items addObject:@{
            @"name": name ? [NSString stringWithUTF8String:name] : @"",
            @"attributes": attributes ? [NSString stringWithUTF8String:attributes] : @"",
        }];
    }
    free(properties);
    return items;
}

static NSArray<NSString *> *AdoptedProtocolsForProtocol(Protocol *protocol) {
    unsigned int count = 0;
    Protocol *__unsafe_unretained *protocols = protocol_copyProtocolList(protocol, &count);
    NSMutableArray<NSString *> *items = [NSMutableArray array];
    for (unsigned int index = 0; index < count; index += 1) {
        const char *name = protocol_getName(protocols[index]);
        if (name) {
            [items addObject:[NSString stringWithUTF8String:name]];
        }
    }
    free(protocols);
    [items sortUsingSelector:@selector(compare:)];
    return items;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        for (int i = 1; i < argc; i += 1) {
            [args addObject:[NSString stringWithUTF8String:argv[i]]];
        }

        NSString *className = ArgValue(args, @"--class", @"");
        NSString *protocolName = ArgValue(args, @"--protocol", @"");
        if (!className.length && !protocolName.length) {
            className = @"IMSPISimulatedMessage";
        }
        [NSApplication sharedApplication];
        dlopen("/System/Library/PrivateFrameworks/IMCore.framework/IMCore", RTLD_LAZY);
        dlopen("/System/Library/PrivateFrameworks/IMDaemonCore.framework/IMDaemonCore", RTLD_LAZY);
        NSMutableDictionary *payload = [NSMutableDictionary dictionary];

        if (className.length) {
            Class cls = NSClassFromString(className);
            payload[@"class_name"] = className;
            payload[@"class_found"] = @(cls != Nil);
            payload[@"instance_methods"] = cls ? SelectorNamesForClass(cls, NO) : @[];
            payload[@"class_methods"] = cls ? SelectorNamesForClass(cls, YES) : @[];
            payload[@"properties"] = cls ? PropertiesForClass(cls) : @[];
        }

        if (protocolName.length) {
            Protocol *protocol = objc_getProtocol([protocolName UTF8String]);
            payload[@"protocol_name"] = protocolName;
            payload[@"protocol_found"] = @(protocol != NULL);
            payload[@"protocols"] = protocol ? AdoptedProtocolsForProtocol(protocol) : @[];
            payload[@"protocol_properties"] = protocol ? PropertiesForProtocol(protocol) : @[];
            payload[@"required_instance_methods"] = protocol ? MethodDescriptionsForProtocol(protocol, YES, YES) : @[];
            payload[@"required_class_methods"] = protocol ? MethodDescriptionsForProtocol(protocol, YES, NO) : @[];
            payload[@"optional_instance_methods"] = protocol ? MethodDescriptionsForProtocol(protocol, NO, YES) : @[];
            payload[@"optional_class_methods"] = protocol ? MethodDescriptionsForProtocol(protocol, NO, NO) : @[];
        }

        NSData *json = [NSJSONSerialization dataWithJSONObject:payload options:NSJSONWritingPrettyPrinted error:nil];
        fwrite([json bytes], 1, [json length], stdout);
        fputc('\n', stdout);
    }
    return 0;
}
