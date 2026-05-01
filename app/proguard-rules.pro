# Keep generic signatures for Retrofit / kotlinx.serialization
-keepattributes Signature, *Annotation*, InnerClasses

# kotlinx.serialization
-keepclassmembers class **$$serializer { *; }
-keepclasseswithmembers class * { @kotlinx.serialization.Serializable <methods>; }
-keep,includedescriptorclasses class com.ontrack.**$$serializer { *; }

# Room
-keep class androidx.room.** { *; }
-keep @androidx.room.* class * { *; }
